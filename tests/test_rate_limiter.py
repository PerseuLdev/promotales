"""Testes para rate limiter"""

import pytest
import time
from src.utils.rate_limiter import RateLimiter
from src.exceptions import RateLimitExceededException


class TestRateLimiter:
    """Testes para RateLimiter"""
    
    def test_allows_requests_within_limit(self):
        """Testa que permite requisições dentro do limite"""
        limiter = RateLimiter(max_requests=5, time_window=60)
        user_id = 12345
        
        # Deve permitir 5 requisições
        for _ in range(5):
            limiter.check_rate_limit(user_id)  # Não deve lançar exceção
    
    def test_blocks_requests_exceeding_limit(self):
        """Testa que bloqueia requisições que excedem o limite"""
        limiter = RateLimiter(max_requests=3, time_window=60)
        user_id = 12345
        
        # Permite 3 requisições
        for _ in range(3):
            limiter.check_rate_limit(user_id)
        
        # Quarta requisição deve ser bloqueada
        with pytest.raises(RateLimitExceededException) as exc_info:
            limiter.check_rate_limit(user_id)
        
        assert exc_info.value.user_id == user_id
        assert exc_info.value.wait_time > 0
    
    def test_resets_after_time_window(self):
        """Testa que reseta após a janela de tempo"""
        limiter = RateLimiter(max_requests=2, time_window=1)  # 1 segundo
        user_id = 12345
        
        # Usa o limite
        for _ in range(2):
            limiter.check_rate_limit(user_id)
        
        # Deve bloquear
        with pytest.raises(RateLimitExceededException):
            limiter.check_rate_limit(user_id)
        
        # Aguarda a janela passar
        time.sleep(1.1)
        
        # Deve permitir novamente
        limiter.check_rate_limit(user_id)  # Não deve lançar exceção
    
    def test_different_users_have_separate_limits(self):
        """Testa que usuários diferentes têm limites separados"""
        limiter = RateLimiter(max_requests=2, time_window=60)
        user1 = 123
        user2 = 456
        
        # User1 usa o limite
        for _ in range(2):
            limiter.check_rate_limit(user1)
        
        # User1 deve ser bloqueado
        with pytest.raises(RateLimitExceededException):
            limiter.check_rate_limit(user1)
        
        # User2 ainda pode fazer requisições
        limiter.check_rate_limit(user2)  # Não deve lançar exceção
    
    def test_get_remaining_requests(self):
        """Testa contagem de requisições restantes"""
        limiter = RateLimiter(max_requests=5, time_window=60)
        user_id = 12345
        
        assert limiter.get_remaining_requests(user_id) == 5
        
        limiter.check_rate_limit(user_id)
        assert limiter.get_remaining_requests(user_id) == 4
        
        limiter.check_rate_limit(user_id)
        assert limiter.get_remaining_requests(user_id) == 3
    
    def test_reset_user(self):
        """Testa reset de usuário específico"""
        limiter = RateLimiter(max_requests=2, time_window=60)
        user_id = 12345
        
        # Usa o limite
        for _ in range(2):
            limiter.check_rate_limit(user_id)
        
        # Deve bloquear
        with pytest.raises(RateLimitExceededException):
            limiter.check_rate_limit(user_id)
        
        # Reseta o usuário
        limiter.reset_user(user_id)
        
        # Deve permitir novamente
        limiter.check_rate_limit(user_id)  # Não deve lançar exceção
    
    def test_clear_all(self):
        """Testa limpeza de todos os limites"""
        limiter = RateLimiter(max_requests=1, time_window=60)
        user1 = 123
        user2 = 456
        
        # Usa o limite para ambos
        limiter.check_rate_limit(user1)
        limiter.check_rate_limit(user2)
        
        # Limpa tudo
        limiter.clear_all()
        
        # Ambos devem poder fazer requisições novamente
        limiter.check_rate_limit(user1)
        limiter.check_rate_limit(user2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
