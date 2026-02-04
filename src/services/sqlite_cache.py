"""
SQLite Cache Service para PromoTales Bot.
Cache persistente usando SQLite para ambiente de produção com baixo consumo de memória.
"""

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from src.models.item_offer import ItemOffer, ItemSearchResult
from src.services.cache_service import BaseCache
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SQLiteCache(BaseCache):
    """
    Implementação de cache persistente usando SQLite.
    Thread-safe com connection-per-thread pattern.
    """

    def __init__(self, db_path: str = "data/cache.db", default_ttl: int = 300):
        """
        Inicializa o cache SQLite.

        Args:
            db_path: Caminho para o arquivo do banco de dados
            default_ttl: TTL padrão em segundos (default: 300 = 5 minutos)
        """
        self._db_path = Path(db_path)
        self._default_ttl = default_ttl
        self._local = threading.local()
        self._hits = 0
        self._misses = 0
        self._stats_lock = threading.Lock()

        # Cria diretório se não existir
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Inicializa o schema
        self._init_schema()

        logger.info(f"SQLiteCache iniciado: {self._db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna conexão thread-local."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self._db_path),
                timeout=30.0,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            # Otimizações para performance
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection.execute("PRAGMA cache_size=1000")
        return self._local.connection

    @contextmanager
    def _cursor(self):
        """Context manager para cursor com commit automático."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_schema(self) -> None:
        """Cria as tabelas se não existirem."""
        with self._cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    ttl INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_expiry
                ON cache(created_at, ttl)
            """)

    def _normalize_key(self, key: str) -> str:
        """Normaliza a chave (lowercase e strip)."""
        return key.lower().strip()

    def _serialize(self, value: Any) -> str:
        """Serializa valor para JSON."""
        if isinstance(value, ItemSearchResult):
            return json.dumps(self._item_search_result_to_dict(value), ensure_ascii=False)
        return json.dumps(value, ensure_ascii=False, default=str)

    def _deserialize(self, data: str) -> Any:
        """Deserializa JSON para objeto."""
        parsed = json.loads(data)
        # Tenta reconstruir ItemSearchResult
        if isinstance(parsed, dict) and "item_nome" in parsed and "ofertas" in parsed:
            return self._dict_to_item_search_result(parsed)
        return parsed

    def _item_offer_to_dict(self, offer: ItemOffer) -> dict:
        """Converte ItemOffer para dicionário."""
        return {
            "nome": offer.nome,
            "preco": offer.preco,
            "localizacao": offer.localizacao,
            "refinamento": offer.refinamento,
            "cartas": offer.cartas,
            "bonus_aleatorios": offer.bonus_aleatorios,
            "vendedor": offer.vendedor,
            "descricao_loja": offer.descricao_loja,
            "quantidade": offer.quantidade,
            "item_id": offer.item_id
        }

    def _dict_to_item_offer(self, d: dict) -> ItemOffer:
        """Reconstrói ItemOffer a partir de dicionário."""
        return ItemOffer(
            nome=d.get("nome", ""),
            preco=d.get("preco", 0),
            localizacao=d.get("localizacao", ""),
            refinamento=d.get("refinamento", 0),
            cartas=d.get("cartas", []),
            bonus_aleatorios=d.get("bonus_aleatorios", []),
            vendedor=d.get("vendedor", ""),
            descricao_loja=d.get("descricao_loja", ""),
            quantidade=d.get("quantidade", 1),
            item_id=d.get("item_id")
        )

    def _item_search_result_to_dict(self, result: ItemSearchResult) -> dict:
        """Converte ItemSearchResult para dicionário."""
        return {
            "item_nome": result.item_nome,
            "ofertas": [self._item_offer_to_dict(o) for o in result.ofertas],
            "preco_medio": result.preco_medio,
            "volume_vendas": result.volume_vendas,
            # price_history é ignorado por simplicidade (pode ser recalculado)
        }

    def _dict_to_item_search_result(self, d: dict) -> ItemSearchResult:
        """Reconstrói ItemSearchResult a partir de dicionário."""
        return ItemSearchResult(
            item_nome=d.get("item_nome", ""),
            ofertas=[self._dict_to_item_offer(o) for o in d.get("ofertas", [])],
            preco_medio=d.get("preco_medio"),
            volume_vendas=d.get("volume_vendas"),
            price_history=None
        )

    def _is_expired(self, created_at: float, ttl: int) -> bool:
        """Verifica se entrada expirou."""
        return time.time() - created_at > ttl

    def get(self, key: str) -> Optional[Any]:
        """
        Busca um valor no cache pela chave.

        Args:
            key: Chave de busca (será normalizada)

        Returns:
            Valor armazenado ou None se não encontrado/expirado
        """
        normalized_key = self._normalize_key(key)

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT value, created_at, ttl FROM cache WHERE key = ?",
                (normalized_key,)
            )
            row = cursor.fetchone()

            if row is None:
                with self._stats_lock:
                    self._misses += 1
                return None

            if self._is_expired(row["created_at"], row["ttl"]):
                cursor.execute("DELETE FROM cache WHERE key = ?", (normalized_key,))
                with self._stats_lock:
                    self._misses += 1
                return None

            with self._stats_lock:
                self._hits += 1

            return self._deserialize(row["value"])

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Salva um valor no cache.

        Args:
            key: Chave de armazenamento (será normalizada)
            value: Valor a ser armazenado
            ttl: TTL em segundos (usa default se não especificado)
        """
        normalized_key = self._normalize_key(key)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        serialized = self._serialize(value)

        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, created_at, ttl)
                VALUES (?, ?, ?, ?)
                """,
                (normalized_key, serialized, time.time(), effective_ttl)
            )

    def invalidate(self, key: str) -> bool:
        """
        Remove uma entrada específica do cache.

        Args:
            key: Chave a ser removida (será normalizada)

        Returns:
            True se a entrada existia e foi removida, False caso contrário
        """
        normalized_key = self._normalize_key(key)

        with self._cursor() as cursor:
            cursor.execute("DELETE FROM cache WHERE key = ?", (normalized_key,))
            return cursor.rowcount > 0

    def clear(self) -> None:
        """Limpa todo o cache."""
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM cache")

        with self._stats_lock:
            self._hits = 0
            self._misses = 0

        logger.info("Cache SQLite limpo")

    def cleanup(self) -> int:
        """
        Remove todas as entradas expiradas.

        Returns:
            Número de entradas removidas
        """
        now = time.time()

        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM cache WHERE (? - created_at) > ttl",
                (now,)
            )
            removed = cursor.rowcount

        if removed > 0:
            logger.debug(f"Cleanup: {removed} entradas expiradas removidas")

        return removed

    def exists(self, key: str) -> bool:
        """
        Verifica se uma chave existe e não está expirada.

        Args:
            key: Chave a verificar (será normalizada)

        Returns:
            True se existe e não expirou
        """
        normalized_key = self._normalize_key(key)

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT created_at, ttl FROM cache WHERE key = ?",
                (normalized_key,)
            )
            row = cursor.fetchone()

            if row is None:
                return False

            if self._is_expired(row["created_at"], row["ttl"]):
                cursor.execute("DELETE FROM cache WHERE key = ?", (normalized_key,))
                return False

            return True

    def size(self) -> int:
        """Retorna o número de entradas no cache (incluindo expiradas)."""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM cache")
            return cursor.fetchone()["count"]

    def stats(self) -> dict:
        """
        Retorna estatísticas do cache.

        Returns:
            Dict com hits, misses, hit_rate e size
        """
        with self._stats_lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "size": self.size(),
                "total_requests": total,
                "db_path": str(self._db_path)
            }

    def get_entry_info(self, key: str) -> Optional[dict]:
        """
        Retorna informações sobre uma entrada específica.

        Args:
            key: Chave da entrada (será normalizada)

        Returns:
            Dict com informações ou None se não existir
        """
        normalized_key = self._normalize_key(key)

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT created_at, ttl FROM cache WHERE key = ?",
                (normalized_key,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            created_at = row["created_at"]
            ttl = row["ttl"]
            remaining = max(0, ttl - (time.time() - created_at))

            return {
                "key": normalized_key,
                "created_at": created_at,
                "ttl": ttl,
                "remaining_ttl": round(remaining, 2),
                "is_expired": self._is_expired(created_at, ttl)
            }

    def close(self) -> None:
        """Fecha a conexão do thread atual."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    def vacuum(self) -> None:
        """Otimiza o banco de dados (VACUUM)."""
        conn = self._get_connection()
        conn.execute("VACUUM")
        logger.info("VACUUM executado no cache SQLite")
