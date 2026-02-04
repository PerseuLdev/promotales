"""Configurações centralizadas do bot"""

import os
from typing import Optional
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()


class Settings:
    """Classe de configurações do bot"""

    # Telegram
    BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")

    # Ambiente
    IS_RENDER: bool = bool(os.environ.get('RENDER'))
    IS_ORACLE: bool = bool(os.environ.get('ORACLE_CLOUD'))
    IS_PRODUCTION: bool = IS_RENDER or IS_ORACLE or os.getenv("ENVIRONMENT") == "production"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production" if IS_PRODUCTION else "local")

    # Cache
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutos
    CACHE_TYPE: str = os.getenv("CACHE_TYPE", "sqlite" if IS_PRODUCTION else "memory")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "data/cache.db")

    # Browser Pool
    BROWSER_POOL_SIZE: int = int(os.getenv("BROWSER_POOL_SIZE", "1"))
    HEADLESS: bool = IS_PRODUCTION or os.getenv("HEADLESS", "false").lower() == "true"

    # Job Queue
    MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "10"))

    # Chrome - paths por ambiente
    CHROME_BINARY_LOCAL: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    CHROME_BINARY_RENDER: str = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    CHROME_BINARY_ORACLE: str = os.environ.get("CHROME_BIN", "/usr/bin/chromium-browser")
    
    # Ragnatales
    RAGNATALES_URL: str = "https://ragnatales.com.br/db/items"
    
    # Timeouts (em segundos) - Total ~15s
    PAGE_LOAD_TIMEOUT: int = 7  # Tempo para Cloudflare resolver
    SEARCH_TIMEOUT: int = 3
    CLICK_TIMEOUT: int = 2
    SHOPS_TIMEOUT: int = 3
    
    # Chrome Options
    CHROME_WINDOW_SIZE: str = "--window-size=1920,1080"
    
    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = 5
    RATE_LIMIT_WINDOW: int = 60  # segundos
    
    @classmethod
    def get_chrome_binary(cls) -> str:
        """Retorna o path do Chrome baseado no ambiente."""
        if cls.IS_ORACLE:
            return cls.CHROME_BINARY_ORACLE
        elif cls.IS_RENDER:
            return cls.CHROME_BINARY_RENDER
        return cls.CHROME_BINARY_LOCAL

    @classmethod
    def validate(cls) -> bool:
        """
        Valida se as configurações necessárias estão presentes

        Returns:
            bool: True se as configurações estão válidas

        Raises:
            ValueError: Se alguma configuração obrigatória estiver ausente
        """
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN não encontrado nas variáveis de ambiente")
        return True

    @classmethod
    def info(cls) -> dict:
        """Retorna informações sobre a configuração atual."""
        return {
            "environment": cls.ENVIRONMENT,
            "is_production": cls.IS_PRODUCTION,
            "cache_type": cls.CACHE_TYPE,
            "headless": cls.HEADLESS,
            "browser_pool_size": cls.BROWSER_POOL_SIZE,
            "chrome_binary": cls.get_chrome_binary()
        }
