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
    co.set_argument('--incognito')  # Modo incognito para nao manter estado entre sessoes

    # Economia de memoria
    co.set_argument('--disable-extensions')
    co.set_argument('--disable-plugins')
    co.set_argument('--disable-background-networking')
    co.set_argument('--disable-sync')
    co.set_argument('--disable-translate')
    co.set_argument('--disable-default-apps')
    co.set_argument('--mute-audio')
    co.set_argument('--no-first-run')
    co.set_argument('--no-default-browser-check')
    co.set_argument('--disable-hang-monitor')
    co.set_argument('--disable-popup-blocking')
    co.set_argument('--disable-prompt-on-repost')
    co.set_argument('--disable-background-timer-throttling')
    co.set_argument('--disable-renderer-backgrounding')
    co.set_argument('--disable-backgrounding-occluded-windows')
    co.set_argument('--disable-features=TranslateUI')
    co.set_argument('--disable-ipc-flooding-protection')
    co.set_argument('--memory-pressure-off')
    co.set_argument('--js-flags=--max-old-space-size=512')  # Limita heap JS a 512MB
    co.set_argument('--renderer-process-limit=1')  # Limita processos de renderizacao

    # Configuracao especifica por ambiente
    if Settings.IS_ORACLE:
        # Oracle Cloud: usa Xvfb (tela virtual), sem headless para passar Cloudflare
        co.set_browser_path(Settings.CHROME_BINARY_ORACLE)
        logger.info("Browser configurado para Oracle Cloud (Xvfb)")
    elif Settings.IS_RENDER:
        # Render: usa headless
        co.headless()
        co.set_browser_path(Settings.CHROME_BINARY_RENDER)
        logger.info("Browser configurado para Render (headless)")
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
