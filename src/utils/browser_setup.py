"""Configuracao do Browser com DrissionPage"""

from DrissionPage import ChromiumPage, ChromiumOptions

from ..config.settings import Settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


def setup_browser_options() -> ChromiumOptions:
    """
    Configura opcoes do Chromium para DrissionPage

    Returns:
        ChromiumOptions: Objeto de opcoes configurado
    """
    co = ChromiumOptions()

    # Configuracoes comuns
    co.set_argument('--disable-gpu')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--window-size=1920,1080')

    # Configuracao especifica por ambiente
    if Settings.IS_RENDER:
        # No Render (cloud), precisa de headless
        co.headless()
        co.set_browser_path(Settings.CHROME_BINARY_RENDER)
        logger.info("Browser configurado para Render (cloud)")
    else:
        # Local: sem headless para passar verificacao Cloudflare
        co.set_browser_path(Settings.CHROME_BINARY_LOCAL)
        logger.info("Browser configurado para ambiente local (sem headless)")

    return co


def setup_browser() -> ChromiumPage:
    """
    Cria e retorna uma instancia do ChromiumPage

    Returns:
        ChromiumPage: Instancia do browser pronta para uso

    Raises:
        Exception: Se houver erro ao iniciar o browser
    """
    options = setup_browser_options()

    try:
        page = ChromiumPage(options)
        logger.info("DrissionPage ChromiumPage iniciado com sucesso")
        return page
    except Exception as e:
        logger.error(f"Erro ao iniciar browser: {str(e)}")
        raise
