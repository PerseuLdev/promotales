"""Fila de jobs para processamento assíncrono de buscas"""

import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
from typing import Dict, Optional, Any, Callable

from ..utils.logger import get_logger

logger = get_logger(__name__)


class JobStatus(Enum):
    """Status possíveis de um job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SearchJob:
    """Representa um job de busca no market"""

    item_name: str
    chat_id: int
    user_id: int
    message_id: Optional[int] = None  # ID da mensagem "buscando..." para editar
    job_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: JobStatus = JobStatus.PENDING
    result: Optional[Any] = None  # ItemSearchResult quando completado
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Parâmetros opcionais de busca
    refinamento: Optional[int] = None
    faixa_refino: Optional[str] = None  # '0', '4-6', '7-9', '10+'

    def mark_processing(self) -> None:
        """Marca job como em processamento"""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.now()

    def mark_completed(self, result: Any) -> None:
        """Marca job como completado com resultado"""
        self.status = JobStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        """Marca job como falho com mensagem de erro"""
        self.status = JobStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()

    def mark_cancelled(self) -> None:
        """Marca job como cancelado"""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now()

    @property
    def is_finished(self) -> bool:
        """Verifica se o job terminou (sucesso, falha ou cancelado)"""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    @property
    def processing_time(self) -> Optional[float]:
        """Retorna tempo de processamento em segundos"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class LocalJobQueue:
    """
    Fila local de jobs usando threading.Queue

    Thread-safe para uso com workers em threads separadas.
    """

    def __init__(self, max_size: int = 100):
        """
        Inicializa a fila de jobs

        Args:
            max_size: Tamanho máximo da fila (0 = ilimitado)
        """
        self._queue: Queue[SearchJob] = Queue(maxsize=max_size)
        self._results: Dict[str, SearchJob] = {}  # job_id -> SearchJob com resultado
        self._lock = threading.Lock()
        self._callbacks: Dict[str, Callable[[SearchJob], None]] = {}  # job_id -> callback

        logger.info(f"LocalJobQueue inicializada (max_size={max_size})")

    def enqueue(
        self,
        job: SearchJob,
        callback: Optional[Callable[[SearchJob], None]] = None
    ) -> bool:
        """
        Adiciona job à fila

        Args:
            job: Job a ser adicionado
            callback: Função chamada quando job completar (opcional)

        Returns:
            True se adicionado com sucesso, False se fila cheia
        """
        try:
            self._queue.put_nowait(job)

            if callback:
                with self._lock:
                    self._callbacks[job.job_id] = callback

            logger.debug(f"Job enfileirado: {job.job_id} - '{job.item_name}'")
            return True

        except Exception as e:
            logger.error(f"Erro ao enfileirar job: {e}")
            return False

    def dequeue(self, timeout: Optional[float] = None) -> Optional[SearchJob]:
        """
        Remove e retorna próximo job da fila

        Args:
            timeout: Tempo máximo de espera em segundos (None = espera indefinida)

        Returns:
            SearchJob ou None se timeout/fila vazia
        """
        try:
            job = self._queue.get(timeout=timeout)
            job.mark_processing()
            logger.debug(f"Job retirado da fila: {job.job_id} - '{job.item_name}'")
            return job

        except Empty:
            return None

    def complete_job(self, job: SearchJob) -> None:
        """
        Marca job como completo e armazena resultado

        Args:
            job: Job completado (deve ter status COMPLETED ou FAILED)
        """
        with self._lock:
            self._results[job.job_id] = job

            # Executa callback se existir
            callback = self._callbacks.pop(job.job_id, None)

        if callback:
            try:
                callback(job)
            except Exception as e:
                logger.error(f"Erro no callback do job {job.job_id}: {e}")

        # Marca tarefa como concluída na queue
        self._queue.task_done()

        status = "sucesso" if job.status == JobStatus.COMPLETED else "falha"
        logger.debug(f"Job {job.job_id} finalizado com {status}")

    def get_result(self, job_id: str) -> Optional[SearchJob]:
        """
        Busca resultado de um job pelo ID

        Args:
            job_id: ID do job

        Returns:
            SearchJob com resultado ou None se não encontrado
        """
        with self._lock:
            return self._results.get(job_id)

    def clear_result(self, job_id: str) -> bool:
        """
        Remove resultado armazenado de um job

        Args:
            job_id: ID do job

        Returns:
            True se removido, False se não existia
        """
        with self._lock:
            if job_id in self._results:
                del self._results[job_id]
                return True
            return False

    def clear_old_results(self, max_age_seconds: float = 300) -> int:
        """
        Remove resultados mais antigos que max_age_seconds

        Args:
            max_age_seconds: Idade máxima em segundos (default: 5 minutos)

        Returns:
            Número de resultados removidos
        """
        now = datetime.now()
        to_remove = []

        with self._lock:
            for job_id, job in self._results.items():
                if job.completed_at:
                    age = (now - job.completed_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(job_id)

            for job_id in to_remove:
                del self._results[job_id]

        if to_remove:
            logger.debug(f"Removidos {len(to_remove)} resultados antigos")

        return len(to_remove)

    @property
    def pending_count(self) -> int:
        """Retorna número de jobs pendentes na fila"""
        return self._queue.qsize()

    @property
    def results_count(self) -> int:
        """Retorna número de resultados armazenados"""
        with self._lock:
            return len(self._results)

    @property
    def is_empty(self) -> bool:
        """Verifica se a fila está vazia"""
        return self._queue.empty()

    def wait_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Espera todos os jobs serem processados

        Args:
            timeout: Tempo máximo de espera em segundos

        Returns:
            True se todos completaram, False se timeout
        """
        try:
            self._queue.join()
            return True
        except Exception:
            return False
