"""Validadores para inputs do PromoTales Bot"""

import re
from typing import Tuple
from ..exceptions import InvalidItemNameException


class ItemNameValidator:
    """Validador para nomes de itens"""
    
    # Configurações de validação
    MIN_LENGTH = 3
    MAX_LENGTH = 100
    
    # Caracteres permitidos (letras, números, espaços, acentos, hífens)
    ALLOWED_PATTERN = re.compile(r'^[a-zA-ZÀ-ÿ0-9\s\-]+$')
    
    # Padrões perigosos (SQL injection, XSS, etc.)
    DANGEROUS_PATTERNS = [
        re.compile(r'[<>"\']'),           # HTML/XSS
        re.compile(r'(--|\;|\/\*)'),      # SQL injection
        re.compile(r'(\$\{|\{\{)'),       # Template injection
        re.compile(r'(javascript:|data:)', re.IGNORECASE),  # XSS via URL
    ]
    
    @classmethod
    def validate(cls, item_name: str) -> Tuple[bool, str]:
        """
        Valida um nome de item
        
        Args:
            item_name: Nome do item a validar
            
        Returns:
            Tuple[bool, str]: (is_valid, sanitized_name)
            
        Raises:
            InvalidItemNameException: Se o nome for inválido
        """
        # Remove espaços extras
        sanitized = item_name.strip()
        
        # Verifica se está vazio
        if not sanitized:
            raise InvalidItemNameException(item_name, "Nome vazio")
        
        # Verifica tamanho mínimo
        if len(sanitized) < cls.MIN_LENGTH:
            raise InvalidItemNameException(
                item_name, 
                f"Nome muito curto (mínimo {cls.MIN_LENGTH} caracteres)"
            )
        
        # Verifica tamanho máximo
        if len(sanitized) > cls.MAX_LENGTH:
            raise InvalidItemNameException(
                item_name, 
                f"Nome muito longo (máximo {cls.MAX_LENGTH} caracteres)"
            )
        
        # Verifica caracteres permitidos
        if not cls.ALLOWED_PATTERN.match(sanitized):
            raise InvalidItemNameException(
                item_name, 
                "Contém caracteres não permitidos"
            )
        
        # Verifica padrões perigosos
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(sanitized):
                raise InvalidItemNameException(
                    item_name, 
                    "Contém padrões potencialmente perigosos"
                )
        
        # Remove múltiplos espaços consecutivos
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        return True, sanitized
    
    @classmethod
    def sanitize(cls, item_name: str) -> str:
        """
        Sanitiza um nome de item (valida e retorna versão limpa)
        
        Args:
            item_name: Nome do item a sanitizar
            
        Returns:
            str: Nome sanitizado
            
        Raises:
            InvalidItemNameException: Se o nome for inválido
        """
        is_valid, sanitized = cls.validate(item_name)
        return sanitized


def validate_item_name(item_name: str) -> str:
    """
    Função auxiliar para validar e sanitizar nome de item
    
    Args:
        item_name: Nome do item a validar
        
    Returns:
        str: Nome sanitizado
        
    Raises:
        InvalidItemNameException: Se o nome for inválido
    """
    return ItemNameValidator.sanitize(item_name)
