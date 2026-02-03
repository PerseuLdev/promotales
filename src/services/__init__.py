"""Serviços do PromoTales Bot"""

from .monitor_service import MonitorService
from .browser_pool import BrowserManager, get_browser_manager
from .job_queue import SearchJob, JobStatus, LocalJobQueue
from .cache_service import MemoryCache, CacheEntry, BaseCache
from .search_worker import SearchWorker, SearchWorkerPool

__all__ = [
    'MonitorService',
    'BrowserManager',
    'get_browser_manager',
    'SearchJob',
    'JobStatus',
    'LocalJobQueue',
    'MemoryCache',
    'CacheEntry',
    'BaseCache',
    'SearchWorker',
    'SearchWorkerPool',
]
