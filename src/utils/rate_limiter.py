"""Rate limiter para controle de requisições por usuário"""

import time
from typing import Dict, List
from collections import defaultdict
from ..exceptions import RateLimitExceededException
from .logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Implementa rate limiting baseado em sliding window
    
    Limita o número de requisições por usuário em um período de tempo.
    """
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        """
        Inicializa o rate limiter
        
        Args:
            max_requests: Número máximo de requisições permitidas
            time_window: Janela de tempo em segundos (padrão: 60s = 1 minuto)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        
        # Armazena timestamps de requisições por usuário
        # user_id -> [timestamp1, timestamp2, ...]
        self._requests: Dict[int, List[float]] = defaultdict(list)
        
        logger.info(
            f"Rate limiter inicializado: {max_requests} requisições por {time_window}s"
        )
    
    def _clean_old_requests(self, user_id: int, current_time: float) -> None:
        """
        Remove requisições antigas fora da janela de tempo
        
        Args:
            user_id: ID do usuário
            current_time: Timestamp atual
        """
        cutoff_time = current_time - self.time_window
        
        # Remove timestamps antigos
        self._requests[user_id] = [
            timestamp for timestamp in self._requests[user_id]
            if timestamp > cutoff_time
        ]
    
    def check_rate_limit(self, user_id: int) -> None:
        """
        Verifica se o usuário pode fazer uma requisição
        
        Args:
            user_id: ID do usuário do Telegram
            
        Raises:
            RateLimitExceededException: Se o limite for excedido
        """
        current_time = time.time()
        
        # Limpa requisições antigas
        self._clean_old_requests(user_id, current_time)
        
        # Verifica número de requisições na janela
        request_count = len(self._requests[user_id])
        
        if request_count >= self.max_requests:
            # Calcula tempo de espera
            oldest_request = self._requests[user_id][0]
            wait_time = int(self.time_window - (current_time - oldest_request)) + 1
            
            logger.warning(
                f"Rate limit excedido para usuário {user_id}. "
                f"Requisições: {request_count}/{self.max_requests}. "
                f"Aguardar: {wait_time}s"
            )
            
            raise RateLimitExceededException(user_id, wait_time)
        
        # Registra a requisição
        self._requests[user_id].append(current_time)
        
        logger.debug(
            f"Requisição registrada para usuário {user_id}. "
            f"Total na janela: {request_count + 1}/{self.max_requests}"
        )
    
    def get_remaining_requests(self, user_id: int) -> int:
        """
        Retorna o número de requisições restantes para o usuário
        
        Args:
            user_id: ID do usuário
            
        Returns:
            int: Número de requisições restantes
        """
        current_time = time.time()
        self._clean_old_requests(user_id, current_time)
        
        current_count = len(self._requests[user_id])
        return max(0, self.max_requests - current_count)
    
    def get_reset_time(self, user_id: int) -> int:
        """
        Retorna o tempo em segundos até o reset do rate limit
        
        Args:
            user_id: ID do usuário
            
        Returns:
            int: Segundos até o reset (0 se não houver requisições)
        """
        current_time = time.time()
        self._clean_old_requests(user_id, current_time)
        
        if not self._requests[user_id]:
            return 0
        
        oldest_request = self._requests[user_id][0]
        reset_time = int(self.time_window - (current_time - oldest_request)) + 1
        
        return max(0, reset_time)
    
    def reset_user(self, user_id: int) -> None:
        """
        Reseta o contador de um usuário específico
        
        Args:
            user_id: ID do usuário
        """
        if user_id in self._requests:
            del self._requests[user_id]
            logger.info(f"Rate limit resetado para usuário {user_id}")
    
    def clear_all(self) -> None:
        """Limpa todos os registros de rate limiting"""
        self._requests.clear()
        logger.info("Todos os rate limits foram resetados")


# Instância global do rate limiter (5 requisições por minuto)
global_rate_limiter = RateLimiter(max_requests=5, time_window=60)
