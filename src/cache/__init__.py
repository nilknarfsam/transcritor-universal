"""Cache Intelligence Engine — reutilização determinística de pipeline."""

from src.cache.cache_engine import CacheEngine, CacheLookupResult
from src.cache.hash_manager import file_fingerprint

__all__ = ["CacheEngine", "CacheLookupResult", "file_fingerprint"]
