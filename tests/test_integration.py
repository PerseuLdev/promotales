"""Testes de integração para Milestone 2"""

import pytest
from src.exceptions import InvalidItemNameException, RateLimitExceededException
from src.utils.validators import validate_item_name
from src.utils.rate_limiter import RateLimiter
from src.utils.logger import get_logger


class TestMilestone2Integration:
    """Testes de integração das funcionalidades da Milestone 2"""
    
    def test_full_workflow_valid_item(self):
        """Testa fluxo completo com item válido"""
        logger = get_logger("test")
        limiter = RateLimiter(max_requests=5, time_window=60)
        user_id = 99999
        
        # 1. Validação
        raw_input = "  Poção Vermelha  "
        clean_name = validate_item_name(raw_input)
        assert clean_name == "Poção Vermelha"
        
        # 2. Rate limiting
        limiter.check_rate_limit(user_id)  # Deve passar
        
        # 3. Logging
        logger.info(f"Busca validada: {clean_name}")
        
        # Sucesso!
    
    def test_full_workflow_invalid_item(self):
        """Testa fluxo completo com item inválido"""
        logger = get_logger("test")
        
        # Input malicioso
        raw_input = "<script>alert('xss')</script>"
        
        with pytest.raises(InvalidItemNameException) as exc_info:
            clean_name = validate_item_name(raw_input)
        
        # Log do erro
        logger.warning(f"Input inválido bloqueado: {raw_input}")
        
        assert "caracteres não permitidos" in str(exc_info.value).lower() or \
               "potencialmente perigosos" in str(exc_info.value).lower()
    
    def test_full_workflow_rate_limit(self):
        """Testa fluxo completo com rate limit"""
        logger = get_logger("test")
        limiter = RateLimiter(max_requests=2, time_window=60)
        user_id = 88888
        
        # Usa o limite
        for i in range(2):
            raw_input = f"  Item {i}  "
            clean_name = validate_item_name(raw_input)
            limiter.check_rate_limit(user_id)
            logger.info(f"Busca {i+1}: {clean_name}")
        
        # Terceira requisição deve falhar
        with pytest.raises(RateLimitExceededException) as exc_info:
            limiter.check_rate_limit(user_id)
        
        logger.warning(f"Rate limit para user {user_id}: {exc_info.value.wait_time}s")
        
        assert exc_info.value.user_id == user_id
        assert exc_info.value.wait_time > 0
    
    def test_validator_and_limiter_separate_concerns(self):
        """Testa que validador e limiter são independentes"""
        limiter = RateLimiter(max_requests=1, time_window=60)
        user_id = 77777
        
        # Validação deve falhar antes do rate limit
        with pytest.raises(InvalidItemNameException):
            clean_name = validate_item_name("AB")  # Muito curto
            limiter.check_rate_limit(user_id)  # Não deve chegar aqui
        
        # Rate limit não deve ter sido afetado
        remaining = limiter.get_remaining_requests(user_id)
        assert remaining == 1  # Limite não foi consumido
    
    def test_logging_doesnt_crash(self):
        """Testa que logging não quebra o fluxo"""
        logger = get_logger("test_safe")
        
        # Logging de diferentes níveis
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Logging com exceção
        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.error("Caught error", exc_info=True)
        
        # Se chegou aqui, logging não quebrou nada
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
