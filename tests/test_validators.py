"""Testes para validadores"""

import pytest
from src.utils.validators import ItemNameValidator, validate_item_name
from src.exceptions import InvalidItemNameException


class TestItemNameValidator:
    """Testes para ItemNameValidator"""
    
    def test_valid_item_name(self):
        """Testa validação de nome válido"""
        valid_names = [
            "Poção Vermelha",
            "Anel de Brilhante",
            "Elmo do Guardião",
            "Espada Longa",
            "Item-Teste",
            "Item 123"
        ]
        
        for name in valid_names:
            is_valid, sanitized = ItemNameValidator.validate(name)
            assert is_valid is True
            assert isinstance(sanitized, str)
    
    def test_sanitize_removes_extra_spaces(self):
        """Testa se remove espaços extras"""
        result = ItemNameValidator.sanitize("  Poção   Vermelha  ")
        assert result == "Poção Vermelha"
    
    def test_empty_name_raises_exception(self):
        """Testa se nome vazio lança exceção"""
        with pytest.raises(InvalidItemNameException) as exc_info:
            ItemNameValidator.validate("")
        
        assert "Nome vazio" in str(exc_info.value)
    
    def test_short_name_raises_exception(self):
        """Testa se nome muito curto lança exceção"""
        with pytest.raises(InvalidItemNameException) as exc_info:
            ItemNameValidator.validate("AB")
        
        assert "muito curto" in str(exc_info.value)
    
    def test_long_name_raises_exception(self):
        """Testa se nome muito longo lança exceção"""
        long_name = "A" * 101
        
        with pytest.raises(InvalidItemNameException) as exc_info:
            ItemNameValidator.validate(long_name)
        
        assert "muito longo" in str(exc_info.value)
    
    def test_dangerous_characters_raise_exception(self):
        """Testa se caracteres perigosos lançam exceção"""
        dangerous_names = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE items; --",
            "Item${user.name}",
            "javascript:alert(1)",
            'Item"OR"1"="1'
        ]
        
        for name in dangerous_names:
            with pytest.raises(InvalidItemNameException):
                ItemNameValidator.validate(name)
    
    def test_validate_item_name_function(self):
        """Testa função auxiliar validate_item_name"""
        result = validate_item_name("  Poção Vermelha  ")
        assert result == "Poção Vermelha"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
