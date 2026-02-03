"""Browser Pool - Gerenciador singleton de browser para reutilização"""

import threading
import time
from typing import Optional

from DrissionPage import ChromiumPage

from ..utils.browser_setup import setup_browser
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BrowserManager:
    """
    Singleton que gerencia uma única instância do browser.

    Permite reutilização do browser entre múltiplas buscas,
    reduzindo overhead de inicialização (~300MB RAM por instância).

    Thread-safe para uso com múltiplas threads.

    Exemplo de uso:
        manager = BrowserManager()
        browser = manager.get_browser()
        # usa o browser...
        manager.release_browser()
    """

    _instance: Optional['BrowserManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'BrowserManager':
        """Implementa padrão Singleton thread-safe"""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Inicializa o gerenciador (executado apenas uma vez)"""
        if self._initialized:
            return

        self._browser: Optional[ChromiumPage] = None
        self._browser_lock = threading.Lock()
        self._in_use = False
        self._use_count = 0
        self._last_used: float = 0
        self._max_uses_before_restart = 50  # Reinicia após N usos para evitar memory leak
        self._initialized = True

        logger.info("BrowserManager singleton inicializado")

    def get_browser(self, wait_timeout: float = 30.0) -> ChromiumPage:
        """
        Obtém a instância do browser (cria se necessário).

        Aguarda se o browser estiver em uso por outra thread.

        Args:
            wait_timeout: Tempo máximo de espera em segundos

        Returns:
            ChromiumPage: Instância do browser pronta para uso

        Raises:
            TimeoutError: Se o browser não ficar disponível no tempo limite
            RuntimeError: Se houver erro ao criar o browser
        """
        start_time = time.time()

        while True:
            with self._browser_lock:
                if not self._in_use:
                    self._in_use = True

                    # Verifica se precisa reiniciar
                    if self._should_restart():
                        self._restart_browser_internal()

                    # Cria browser se não existir
                    if self._browser is None:
                        self._create_browser_internal()

                    self._use_count += 1
                    self._last_used = time.time()
                    logger.debug(f"Browser adquirido (uso #{self._use_count})")
                    return self._browser

            # Browser está em uso, aguarda
            elapsed = time.time() - start_time
            if elapsed >= wait_timeout:
                raise TimeoutError(
                    f"Timeout aguardando browser ficar disponível ({wait_timeout}s)"
                )

            time.sleep(0.1)  # Pequena pausa antes de tentar novamente

    def release_browser(self) -> None:
        """
        Libera o browser para uso por outras threads.

        Deve ser chamado após terminar de usar o browser.
        """
        with self._browser_lock:
            if self._in_use:
                self._in_use = False
                logger.debug("Browser liberado")
            else:
                logger.warning("release_browser() chamado mas browser não estava em uso")

    def restart_if_needed(self, force: bool = False) -> bool:
        """
        Reinicia o browser se necessário ou forçado.

        Args:
            force: Se True, reinicia mesmo se não houver problemas

        Returns:
            bool: True se reiniciou, False caso contrário
        """
        with self._browser_lock:
            if not self._in_use:
                if force or self._should_restart():
                    self._restart_browser_internal()
                    return True
        return False

    def shutdown(self) -> None:
        """
        Encerra o browser completamente.

        Deve ser chamado no shutdown da aplicação.
        """
        with self._browser_lock:
            self._close_browser_internal()
            self._in_use = False
            self._use_count = 0
            logger.info("BrowserManager encerrado")

    def is_available(self) -> bool:
        """Verifica se o browser está disponível para uso"""
        with self._browser_lock:
            return not self._in_use

    def is_healthy(self) -> bool:
        """
        Verifica se o browser está funcionando corretamente.

        Returns:
            bool: True se o browser está saudável
        """
        with self._browser_lock:
            if self._browser is None:
                return True  # Será criado quando necessário

            try:
                # Tenta acessar propriedade do browser para verificar conexão
                _ = self._browser.url
                return True
            except Exception as e:
                logger.warning(f"Browser não está saudável: {e}")
                return False

    @property
    def stats(self) -> dict:
        """Retorna estatísticas de uso do browser"""
        with self._browser_lock:
            return {
                "in_use": self._in_use,
                "use_count": self._use_count,
                "browser_active": self._browser is not None,
                "last_used": self._last_used,
                "max_uses_before_restart": self._max_uses_before_restart
            }

    def _should_restart(self) -> bool:
        """Verifica se o browser deve ser reiniciado"""
        if self._browser is None:
            return False

        # Reinicia após muitos usos
        if self._use_count >= self._max_uses_before_restart:
            logger.info(f"Browser atingiu {self._use_count} usos, marcado para reinício")
            return True

        # Verifica saúde do browser
        try:
            _ = self._browser.url
        except Exception:
            logger.warning("Browser com problemas, marcado para reinício")
            return True

        return False

    def _create_browser_internal(self) -> None:
        """Cria nova instância do browser (uso interno, sem lock)"""
        try:
            self._browser = setup_browser()
            self._use_count = 0
            logger.info("Browser criado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao criar browser: {e}")
            raise RuntimeError(f"Falha ao criar browser: {e}")

    def _close_browser_internal(self) -> None:
        """Fecha o browser (uso interno, sem lock)"""
        if self._browser is not None:
            try:
                self._browser.quit()
                logger.info("Browser fechado com sucesso")
            except Exception as e:
                logger.warning(f"Erro ao fechar browser: {e}")
            finally:
                self._browser = None

    def _restart_browser_internal(self) -> None:
        """Reinicia o browser (uso interno, sem lock)"""
        logger.info("Reiniciando browser...")
        self._close_browser_internal()
        self._create_browser_internal()


# Instância global para facilitar importação
_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """
    Retorna a instância global do BrowserManager.

    Função auxiliar para facilitar uso sem instanciar diretamente.

    Returns:
        BrowserManager: Instância singleton do gerenciador
    """
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager
