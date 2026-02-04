"""Testes para o SQLite Cache Service"""

import os
import tempfile
import threading
import time

import pytest

from src.services.sqlite_cache import SQLiteCache
from src.models.item_offer import ItemOffer, ItemSearchResult


@pytest.fixture
def temp_db():
    """Cria um banco de dados temporario para testes."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def cache(temp_db):
    """Cria uma instancia de cache para testes."""
    cache = SQLiteCache(db_path=temp_db, default_ttl=60)
    yield cache
    cache.close()


class TestSQLiteCache:
    """Testes basicos do SQLiteCache"""

    def test_set_and_get(self, cache):
        """Testa set e get basico."""
        cache.set("test_key", "test_value")
        result = cache.get("test_key")
        assert result == "test_value"

    def test_get_nonexistent(self, cache):
        """Testa get de chave inexistente."""
        result = cache.get("nonexistent")
        assert result is None

    def test_key_normalization(self, cache):
        """Testa normalizacao de chaves."""
        cache.set("  MANTO da Bruxa  ", "value")
        assert cache.get("manto da bruxa") == "value"
        assert cache.get("MANTO DA BRUXA") == "value"
        assert cache.get("  manto da bruxa  ") == "value"

    def test_ttl_expiration(self, temp_db):
        """Testa expiracao por TTL."""
        cache = SQLiteCache(db_path=temp_db, default_ttl=1)  # 1 segundo
        cache.set("expiring_key", "value")

        # Ainda nao expirou
        assert cache.get("expiring_key") == "value"

        # Espera expirar
        time.sleep(1.5)
        assert cache.get("expiring_key") is None
        cache.close()

    def test_custom_ttl(self, cache):
        """Testa TTL customizado."""
        cache.set("quick_expire", "value", ttl=1)
        time.sleep(1.5)
        assert cache.get("quick_expire") is None

    def test_invalidate(self, cache):
        """Testa invalidacao de chave."""
        cache.set("to_invalidate", "value")
        assert cache.get("to_invalidate") == "value"

        assert cache.invalidate("to_invalidate") is True
        assert cache.get("to_invalidate") is None

        # Invalidar inexistente
        assert cache.invalidate("nonexistent") is False

    def test_clear(self, cache):
        """Testa limpeza do cache."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.size() == 0

    def test_cleanup(self, temp_db):
        """Testa cleanup de expirados."""
        cache = SQLiteCache(db_path=temp_db, default_ttl=1)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        time.sleep(1.5)
        removed = cache.cleanup()
        assert removed == 2
        cache.close()

    def test_exists(self, cache):
        """Testa verificacao de existencia."""
        cache.set("existing", "value")
        assert cache.exists("existing") is True
        assert cache.exists("nonexistent") is False

    def test_size(self, cache):
        """Testa contagem de tamanho."""
        assert cache.size() == 0

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2

    def test_stats(self, cache):
        """Testa estatisticas."""
        cache.get("miss")  # Miss
        cache.set("key", "value")
        cache.get("key")  # Hit

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_entry_info(self, cache):
        """Testa informacoes de entrada."""
        cache.set("info_key", "value", ttl=100)

        info = cache.get_entry_info("info_key")
        assert info is not None
        assert info["key"] == "info_key"
        assert info["ttl"] == 100
        assert info["remaining_ttl"] > 0
        assert info["is_expired"] is False

        assert cache.get_entry_info("nonexistent") is None


class TestSQLiteCacheSerialization:
    """Testes de serializacao de objetos complexos"""

    def test_item_offer_serialization(self, cache):
        """Testa serializacao de ItemOffer."""
        offer = ItemOffer(
            nome="Manto da Bruxa",
            preco=1500000,
            localizacao="@market 50/50",
            refinamento=9,
            cartas=["Carta 1", "Carta 2"],
            bonus_aleatorios=["ATK +10%"],
            vendedor="TestShop",
            descricao_loja="Loja teste",
            quantidade=1,
            item_id="12345"
        )

        result = ItemSearchResult(
            item_nome="Manto da Bruxa",
            ofertas=[offer],
            preco_medio="1.500.000",
            volume_vendas="100"
        )

        cache.set("manto", result)
        retrieved = cache.get("manto")

        assert retrieved is not None
        assert isinstance(retrieved, ItemSearchResult)
        assert retrieved.item_nome == "Manto da Bruxa"
        assert len(retrieved.ofertas) == 1
        assert retrieved.ofertas[0].nome == "Manto da Bruxa"
        assert retrieved.ofertas[0].preco == 1500000
        assert retrieved.ofertas[0].refinamento == 9
        assert retrieved.ofertas[0].cartas == ["Carta 1", "Carta 2"]

    def test_empty_result_serialization(self, cache):
        """Testa serializacao de resultado vazio."""
        result = ItemSearchResult(
            item_nome="Item Inexistente",
            ofertas=[],
            preco_medio=None,
            volume_vendas=None
        )

        cache.set("empty", result)
        retrieved = cache.get("empty")

        assert retrieved is not None
        assert retrieved.item_nome == "Item Inexistente"
        assert len(retrieved.ofertas) == 0


class TestSQLiteCacheThreadSafety:
    """Testes de thread-safety"""

    def test_concurrent_writes(self, cache):
        """Testa escritas concorrentes."""
        errors = []

        def write_values(prefix, count):
            try:
                for i in range(count):
                    cache.set(f"{prefix}_{i}", f"value_{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=write_values, args=(f"thread_{i}", 50))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cache.size() == 250  # 5 threads * 50 valores

    def test_concurrent_reads_writes(self, cache):
        """Testa leituras e escritas concorrentes."""
        errors = []

        def writer():
            try:
                for i in range(100):
                    cache.set(f"key_{i}", f"value_{i}")
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(100):
                    cache.get(f"key_{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
