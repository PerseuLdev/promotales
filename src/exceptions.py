"""Custom exceptions para o PromoTales Bot"""


class PromoTalesException(Exception):
    """Exceção base para todas as exceções do PromoTales"""
    pass


class ItemNotFoundException(PromoTalesException):
    """Exceção lançada quando um item não é encontrado no market"""
    
    def __init__(self, item_name: str):
        self.item_name = item_name
        self.message = f"Item '{item_name}' não encontrado no market"
        super().__init__(self.message)


class InvalidItemNameException(PromoTalesException):
    """Exceção lançada quando o nome do item é inválido"""
    
    def __init__(self, item_name: str, reason: str = "Nome inválido"):
        self.item_name = item_name
        self.reason = reason
        self.message = f"Nome de item inválido '{item_name}': {reason}"
        super().__init__(self.message)


class ScraperException(PromoTalesException):
    """Exceção lançada quando ocorre um erro no scraper"""
    
    def __init__(self, message: str, original_exception: Exception = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)


class BrowserException(ScraperException):
    """Exceção lançada quando há problemas com o Browser (DrissionPage)"""

    def __init__(self, message: str = "Erro ao iniciar Browser"):
        super().__init__(message)


# Alias para compatibilidade retroativa
ChromeDriverException = BrowserException


class PageLoadException(ScraperException):
    """Exceção lançada quando uma página não carrega corretamente"""
    
    def __init__(self, url: str, timeout: int = 10):
        self.url = url
        self.timeout = timeout
        message = f"Timeout ao carregar página '{url}' após {timeout}s"
        super().__init__(message)


class RateLimitExceededException(PromoTalesException):
    """Exceção lançada quando o rate limit é excedido"""
    
    def __init__(self, user_id: int, wait_time: int):
        self.user_id = user_id
        self.wait_time = wait_time
        self.message = f"Rate limit excedido. Aguarde {wait_time} segundos antes de fazer outra busca."
        super().__init__(self.message)


class ConfigurationException(PromoTalesException):
    """Exceção lançada quando há problemas de configuração"""
    
    def __init__(self, config_name: str, message: str = "Configuração ausente ou inválida"):
        self.config_name = config_name
        self.message = f"Erro de configuração '{config_name}': {message}"
        super().__init__(self.message)


class APIException(PromoTalesException):
    """Exceção lançada quando há problemas com a API do Ragnatales"""
    
    def __init__(self, endpoint: str, status_code: int = None, message: str = "Erro na API"):
        self.endpoint = endpoint
        self.status_code = status_code
        self.message = f"Erro ao acessar API '{endpoint}'"
        if status_code:
            self.message += f" (Status: {status_code})"
        self.message += f": {message}"
        super().__init__(self.message)
