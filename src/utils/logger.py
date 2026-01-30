"""Configuração de logging estruturado para o PromoTales Bot"""

import logging
import sys
from typing import Optional
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para melhor visualização no terminal"""
    
    # Códigos de cores ANSI
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Formata o log com cores"""
        # Adiciona cor ao nível do log
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logger(
    name: str = "promotales",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    enable_colors: bool = True
) -> logging.Logger:
    """
    Configura e retorna um logger estruturado
    
    Args:
        name: Nome do logger
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Caminho para arquivo de log (opcional)
        enable_colors: Habilita cores no console
        
    Returns:
        logging.Logger: Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove handlers existentes para evitar duplicação
    logger.handlers.clear()
    
    # Formato do log
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if enable_colors:
        console_formatter = ColoredFormatter(log_format, datefmt=date_format)
    else:
        console_formatter = logging.Formatter(log_format, datefmt=date_format)
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo (se especificado)
    if log_file:
        # Cria diretório se não existir
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger com o nome especificado
    
    Args:
        name: Nome do logger (geralmente __name__)
        
    Returns:
        logging.Logger: Logger configurado
    """
    return logging.getLogger(name)


# Logger padrão do PromoTales
promotales_logger = setup_logger(
    name="promotales",
    level=logging.INFO,
    log_file="logs/promotales.log",
    enable_colors=True
)
