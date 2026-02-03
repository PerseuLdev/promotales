"""
Cache Service para PromoTales Bot.
Implementa cache em memória para reduzir buscas redundantes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Optional
import time


@dataclass
class CacheEntry:
    """Entrada de cache com resultado, timestamp e TTL."""

    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: int = 300  # segundos

    def is_expired(self) -> bool:
        """Verifica se a entrada expirou."""
        return time.time() - self.timestamp > self.ttl

    def remaining_ttl(self) -> float:
        """Retorna o tempo restante em segundos."""
        remaining = self.ttl - (time.time() - self.timestamp)
        return max(0, remaining)


class BaseCache(ABC):
    """Interface abstrata para implementações de cache."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Busca um valor no cache pela chave."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Salva um valor no cache com TTL opcional."""
        pass

    @abstractmethod
    def invalidate(self, key: str) -> bool:
        """Remove uma entrada específica do cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Limpa todo o cache."""
        pass

    @abstractmethod
    def cleanup(self) -> int:
        """Remove entradas expiradas. Retorna quantidade removida."""
        pass


class MemoryCache(BaseCache):
    """Implementação de cache em memória com thread-safety."""

    def __init__(self, default_ttl: int = 300):
        """
        Inicializa o cache em memória.

        Args:
            default_ttl: TTL padrão em segundos (default: 300 = 5 minutos)
        """
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _normalize_key(self, key: str) -> str:
        """Normaliza a chave (lowercase e strip)."""
        return key.lower().strip()

    def get(self, key: str) -> Optional[Any]:
        """
        Busca um valor no cache pela chave.

        Args:
            key: Chave de busca (será normalizada)

        Returns:
            Valor armazenado ou None se não encontrado/expirado
        """
        normalized_key = self._normalize_key(key)

        with self._lock:
            entry = self._cache.get(normalized_key)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                del self._cache[normalized_key]
                self._misses += 1
                return None

            self._hits += 1
            return entry.value

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

        entry = CacheEntry(
            value=value,
            timestamp=time.time(),
            ttl=effective_ttl
        )

        with self._lock:
            self._cache[normalized_key] = entry

    def invalidate(self, key: str) -> bool:
        """
        Remove uma entrada específica do cache.

        Args:
            key: Chave a ser removida (será normalizada)

        Returns:
            True se a entrada existia e foi removida, False caso contrário
        """
        normalized_key = self._normalize_key(key)

        with self._lock:
            if normalized_key in self._cache:
                del self._cache[normalized_key]
                return True
            return False

    def clear(self) -> None:
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cleanup(self) -> int:
        """
        Remove todas as entradas expiradas.

        Returns:
            Número de entradas removidas
        """
        removed = 0

        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                removed += 1

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

        with self._lock:
            entry = self._cache.get(normalized_key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._cache[normalized_key]
                return False
            return True

    def size(self) -> int:
        """Retorna o número de entradas no cache (incluindo expiradas)."""
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict:
        """
        Retorna estatísticas do cache.

        Returns:
            Dict com hits, misses, hit_rate e size
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "size": len(self._cache),
                "total_requests": total
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

        with self._lock:
            entry = self._cache.get(normalized_key)
            if entry is None:
                return None

            return {
                "key": normalized_key,
                "timestamp": datetime.fromtimestamp(entry.timestamp).isoformat(),
                "ttl": entry.ttl,
                "remaining_ttl": round(entry.remaining_ttl(), 2),
                "is_expired": entry.is_expired()
            }
