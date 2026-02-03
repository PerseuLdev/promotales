"""Worker para processamento assíncrono de buscas"""

import threading
import time
from typing import Optional, Callable, Any

from .job_queue import LocalJobQueue, SearchJob, JobStatus
from .cache_service import MemoryCache
from .browser_pool import BrowserManager, get_browser_manager
from ..scraper.ragnatales_scraper import RagnatalesScraper
from ..exceptions import ItemNotFoundException, ScraperException
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SearchWorker:
    """
    Worker thread para processar buscas em background.

    Integra:
    - LocalJobQueue: fila de jobs
    - MemoryCache: cache de resultados
    - BrowserManager: pool de browsers
    - RagnatalesScraper: scraper

    Exemplo de uso:
        queue = LocalJobQueue()
        cache = MemoryCache()
        worker = SearchWorker(queue, cache)
        worker.start()

        # Adiciona jobs à fila
        job = SearchJob(item_name="Gelo Eterno", chat_id=123, user_id=456)
        queue.enqueue(job, callback=on_result)

        # Quando terminar
        worker.stop()
    """

    def __init__(
        self,
        job_queue: LocalJobQueue,
        cache: MemoryCache,
        browser_manager: Optional[BrowserManager] = None,
        result_callback: Optional[Callable[[SearchJob], None]] = None
    ):
        """
        Inicializa o worker.

        Args:
            job_queue: Fila de jobs para processar
            cache: Cache de resultados
            browser_manager: Gerenciador de browser (usa global se não fornecido)
            result_callback: Callback global chamado para cada resultado
        """
        self._queue = job_queue
        self._cache = cache
        self._browser_manager = browser_manager or get_browser_manager()
        self._result_callback = result_callback

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_event = threading.Event()

        # Estatísticas
        self._jobs_processed = 0
        self._cache_hits = 0
        self._errors = 0

        logger.info("SearchWorker inicializado")

    def start(self) -> None:
        """Inicia o worker thread."""
        if self._running:
            logger.warning("Worker já está rodando")
            return

        self._running = True
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._worker_loop,
            name="SearchWorker",
            daemon=True
        )
        self._thread.start()
        logger.info("SearchWorker iniciado")

    def stop(self, timeout: float = 10.0) -> bool:
        """
        Para o worker thread.

        Args:
            timeout: Tempo máximo de espera para o worker finalizar

        Returns:
            True se parou corretamente, False se timeout
        """
        if not self._running:
            return True

        logger.info("Parando SearchWorker...")
        self._running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

            if self._thread.is_alive():
                logger.warning("Worker não parou no tempo limite")
                return False

        logger.info("SearchWorker parado")
        return True

    def is_running(self) -> bool:
        """Verifica se o worker está rodando."""
        return self._running and self._thread is not None and self._thread.is_alive()

    @property
    def stats(self) -> dict:
        """Retorna estatísticas do worker."""
        return {
            "running": self.is_running(),
            "jobs_processed": self._jobs_processed,
            "cache_hits": self._cache_hits,
            "errors": self._errors,
            "pending_jobs": self._queue.pending_count,
            "cache_stats": self._cache.stats(),
            "browser_stats": self._browser_manager.stats
        }

    def _worker_loop(self) -> None:
        """Loop principal do worker."""
        logger.info("Worker loop iniciado")

        while self._running:
            try:
                # Tenta pegar próximo job com timeout
                job = self._queue.dequeue(timeout=1.0)

                if job is None:
                    # Timeout, verifica se deve parar
                    if self._stop_event.is_set():
                        break
                    continue

                # Processa o job
                self._process_job(job)

            except Exception as e:
                logger.error(f"Erro no worker loop: {e}", exc_info=True)
                self._errors += 1
                time.sleep(1)  # Evita loop de erro muito rápido

        logger.info("Worker loop finalizado")

    def _process_job(self, job: SearchJob) -> None:
        """
        Processa um job de busca.

        Args:
            job: Job a ser processado
        """
        item_name = job.item_name
        logger.info(f"Processando job {job.job_id}: '{item_name}'")

        try:
            # Verifica cache primeiro
            cached_result = self._cache.get(item_name)

            if cached_result is not None:
                logger.info(f"Cache hit para '{item_name}'")
                self._cache_hits += 1
                job.mark_completed(cached_result)
                self._finalize_job(job)
                return

            # Cache miss - faz busca real
            logger.info(f"Cache miss para '{item_name}', iniciando busca...")
            result = self._search_item(job)

            if result is not None:
                # Salva no cache
                self._cache.set(item_name, result)
                job.mark_completed(result)
                logger.info(f"Busca concluída para '{item_name}'")
            else:
                job.mark_failed("Item não encontrado")
                logger.warning(f"Item '{item_name}' não encontrado")

        except ItemNotFoundException:
            job.mark_failed(f"Item '{item_name}' não encontrado no market")
            logger.warning(f"Item não encontrado: {item_name}")

        except ScraperException as e:
            job.mark_failed(f"Erro ao buscar: {str(e)}")
            logger.error(f"Erro de scraping para '{item_name}': {e}")
            self._errors += 1

        except Exception as e:
            job.mark_failed(f"Erro inesperado: {str(e)}")
            logger.error(f"Erro inesperado ao processar '{item_name}': {e}", exc_info=True)
            self._errors += 1

        finally:
            self._finalize_job(job)
            self._jobs_processed += 1

    def _search_item(self, job: SearchJob) -> Optional[Any]:
        """
        Executa a busca usando o scraper.

        Args:
            job: Job com informações da busca

        Returns:
            ItemSearchResult ou None
        """
        browser = None

        try:
            # Adquire browser do pool
            browser = self._browser_manager.get_browser(wait_timeout=60.0)

            # Cria scraper com browser externo
            scraper = RagnatalesScraper(browser=browser)

            # Executa busca
            result = scraper.search_item(job.item_name)

            return result

        finally:
            # Sempre libera o browser
            if browser is not None:
                self._browser_manager.release_browser()

    def _finalize_job(self, job: SearchJob) -> None:
        """
        Finaliza o job e executa callbacks.

        Args:
            job: Job finalizado
        """
        # Notifica a fila que o job foi completado
        self._queue.complete_job(job)

        # Executa callback global se existir
        if self._result_callback:
            try:
                self._result_callback(job)
            except Exception as e:
                logger.error(f"Erro no callback global: {e}")

        # Log de tempo de processamento
        if job.processing_time:
            logger.debug(
                f"Job {job.job_id} finalizado em {job.processing_time:.2f}s "
                f"(status: {job.status.value})"
            )


class SearchWorkerPool:
    """
    Pool de workers para processamento paralelo.

    Para uso futuro quando precisar de múltiplos workers.
    """

    def __init__(
        self,
        job_queue: LocalJobQueue,
        cache: MemoryCache,
        worker_count: int = 1,
        result_callback: Optional[Callable[[SearchJob], None]] = None
    ):
        """
        Inicializa o pool de workers.

        Args:
            job_queue: Fila de jobs compartilhada
            cache: Cache compartilhado
            worker_count: Número de workers
            result_callback: Callback para resultados
        """
        self._queue = job_queue
        self._cache = cache
        self._worker_count = worker_count
        self._result_callback = result_callback
        self._workers: list[SearchWorker] = []

        logger.info(f"SearchWorkerPool inicializado com {worker_count} worker(s)")

    def start(self) -> None:
        """Inicia todos os workers."""
        for i in range(self._worker_count):
            worker = SearchWorker(
                job_queue=self._queue,
                cache=self._cache,
                result_callback=self._result_callback
            )
            worker.start()
            self._workers.append(worker)

        logger.info(f"Pool de {len(self._workers)} worker(s) iniciado")

    def stop(self, timeout: float = 10.0) -> bool:
        """
        Para todos os workers.

        Args:
            timeout: Tempo máximo de espera por worker

        Returns:
            True se todos pararam corretamente
        """
        all_stopped = True

        for i, worker in enumerate(self._workers):
            if not worker.stop(timeout=timeout):
                logger.warning(f"Worker {i} não parou no tempo limite")
                all_stopped = False

        self._workers.clear()
        return all_stopped

    @property
    def stats(self) -> dict:
        """Retorna estatísticas agregadas de todos os workers."""
        total_processed = sum(w._jobs_processed for w in self._workers)
        total_cache_hits = sum(w._cache_hits for w in self._workers)
        total_errors = sum(w._errors for w in self._workers)

        return {
            "worker_count": len(self._workers),
            "active_workers": sum(1 for w in self._workers if w.is_running()),
            "total_jobs_processed": total_processed,
            "total_cache_hits": total_cache_hits,
            "total_errors": total_errors,
            "pending_jobs": self._queue.pending_count
        }
