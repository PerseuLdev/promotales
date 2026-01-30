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
    
    # Chrome
    CHROME_BINARY_LOCAL: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    CHROME_BINARY_RENDER: str = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    
    # Ragnatales
    RAGNATALES_URL: str = "https://ragnatales.com.br/db/items"
    
    # Timeouts (em segundos) - Total ~10s
    PAGE_LOAD_TIMEOUT: int = 5  # Tempo para Cloudflare resolver
    SEARCH_TIMEOUT: int = 2
    CLICK_TIMEOUT: int = 1
    SHOPS_TIMEOUT: int = 2
    
    # Chrome Options
    CHROME_WINDOW_SIZE: str = "--window-size=1920,1080"
    
    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = 5
    RATE_LIMIT_WINDOW: int = 60  # segundos
    
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
