"""Configuracao do Chrome e ChromeDriver com anti-deteccao"""

import os
import shutil
import undetected_chromedriver as uc
from selenium.webdriver.remote.webdriver import WebDriver

from ..config.settings import Settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


def _clean_chromedriver_cache() -> None:
    """Remove cache do undetected_chromedriver para evitar conflitos"""
    cache_dir = os.path.join(os.environ.get('APPDATA', ''), 'undetected_chromedriver')
    if os.path.exists(cache_dir):
        try:
            # Remove apenas o arquivo problematico
            exe_path = os.path.join(cache_dir, 'undetected', 'undetected_chromedriver.exe')
            if os.path.exists(exe_path):
                os.remove(exe_path)
                logger.debug(f"Removido cache do chromedriver: {exe_path}")
        except Exception as e:
            logger.warning(f"Nao foi possivel limpar cache do chromedriver: {e}")


def setup_chrome_options() -> uc.ChromeOptions:
    """
    Configura as opcoes do Chrome para ambiente local ou Render

    Returns:
        ChromeOptions: Objeto de opcoes do Chrome configurado
    """
    chrome_options = uc.ChromeOptions()

    # Configuracoes comuns
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(Settings.CHROME_WINDOW_SIZE)

    # Configuracao especifica por ambiente
    if Settings.IS_RENDER:
        # No Render (cloud), precisa de headless
        chrome_options.add_argument("--headless=new")
        chrome_options.binary_location = Settings.CHROME_BINARY_RENDER
        logger.info("Chrome configurado para Render (cloud)")
    else:
        # Local: sem headless para passar verificacao Cloudflare
        chrome_options.binary_location = Settings.CHROME_BINARY_LOCAL
        logger.info("Chrome configurado para ambiente local (sem headless)")

    return chrome_options


def setup_chrome_driver() -> WebDriver:
    """
    Cria e retorna uma instancia do ChromeDriver configurada
    usando undetected-chromedriver para evitar deteccao de bot

    Returns:
        WebDriver: Instancia do ChromeDriver pronta para uso

    Raises:
        Exception: Se houver erro ao iniciar o ChromeDriver
    """
    chrome_options = setup_chrome_options()

    # Limpa cache para evitar erro de arquivo existente
    _clean_chromedriver_cache()

    try:
        # version_main=144 para corresponder ao Chrome instalado
        # use_subprocess=True para melhor compatibilidade
        driver = uc.Chrome(
            options=chrome_options,
            use_subprocess=True,
            version_main=144
        )
        logger.info("ChromeDriver (undetected) iniciado com sucesso")
        return driver
    except Exception as e:
        logger.error(f"Erro ao iniciar ChromeDriver: {str(e)}")
        raise
