from typing import List, Optional, TypeVar, Generic
from datetime import datetime

from .object import HistoryRequest, BarData, TickData


# Type variables for generic cache
T = TypeVar('T', BarData, TickData)


class BaseCacheBackend(Generic[T]):
    """
    Abstract base class for cache backends.
    """
    
    def init(self) -> bool:
        """
        Initialize the cache backend.
        """
        return True
    
    def load_data(self, req: HistoryRequest) -> List[T]:
        """
        Load data from cache.
        """
        return []
    
    def save_data(self, data: List[T]) -> bool:
        """
        Save data to cache.
        """
        return False