from typing import List, Optional, Callable, TypeVar, Generic
from datetime import datetime, timedelta
import asyncio

from .datafeed import BaseDatafeed
from .object import HistoryRequest, BarData, TickData
from .constant import Interval, Exchange
from .locale import _
from .cache_backend import BaseCacheBackend, T
from .parquet_cache_backend import ParquetCacheBackend
from .stock_metadata import StockMetadataManager, DataStatus, StockMetadata


# 导出增强版数据服务
from .enhanced_cached_datafeed import (
    EnhancedCachedDatafeedWrapper,
    create_enhanced_cached_datafeed
)


class DatabaseCacheBackend(BaseCacheBackend[T]):
    """
    Database cache backend implementation.
    """
    
    def __init__(self):
        """
        Initialize database cache backend.
        """
        from .database import get_database
        self.database = get_database()
    
    def load_data(self, req: HistoryRequest) -> List[T]:
        """
        Load data from database cache.
        """
        if isinstance(req.interval, Interval):
            # Bar data
            return self.database.load_bar_data(
                symbol=req.symbol,
                exchange=req.exchange,
                interval=req.interval,
                start=req.start,
                end=req.end or datetime.now()
            )
        else:
            # Tick data
            return self.database.load_tick_data(
                symbol=req.symbol,
                exchange=req.exchange,
                start=req.start,
                end=req.end or datetime.now()
            )
    
    def save_data(self, data: List[T]) -> bool:
        """
        Save data to database cache.
        """
        if data and isinstance(data[0], BarData):
            return self.database.save_bar_data(data)
        elif data and isinstance(data[0], TickData):
            return self.database.save_tick_data(data)
        return False


class CachedDatafeedWrapper(BaseDatafeed):
    """
    Cache wrapper for datafeed. Will:
    1. First query local cache
    2. If cache miss, query from network datafeed
    3. Async cache the network data
    4. Return data to caller immediately
    """
    
    def __init__(self, network_datafeed: BaseDatafeed, cache_backend: Optional[BaseCacheBackend[T]] = None):
        """
        Initialize cached datafeed wrapper.
        
        Parameters:
            network_datafeed: The network datafeed to wrap
            cache_backend: The cache backend to use (default: ParquetCacheBackend)
        """
        self.network_datafeed = network_datafeed
        self.cache_backend = cache_backend or ParquetCacheBackend()
        self.inited = False
        
        # Cache settings
        self.min_cache_length = 10  # Minimum number of bars/ticks to cache
        
        # Async task management
        self._cache_tasks: List[asyncio.Task] = []
    
    def init(self, output: Callable = print) -> bool:
        """
        Initialize both network datafeed and cache backend.
        """
        output(_("Initializing cached datafeed wrapper..."))
        
        # Initialize network datafeed
        if hasattr(self.network_datafeed, 'init'):
            network_init = self.network_datafeed.init(output)
            if not network_init:
                output(_("Warning: Network datafeed initialization failed"))
        
        # Initialize cache backend
        cache_init = self.cache_backend.init()
        if not cache_init:
            output(_("Warning: Cache backend initialization failed"))
        
        self.inited = True
        output(_("Cached datafeed wrapper initialized successfully"))
        return True
    
    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> List[BarData]:
        """
        Query bar history with cache support.
        1. First try to load from cache
        2. If cache doesn't have complete data, query from network datafeed
        3. Async cache the network data
        4. Return merged data to caller
        """
        if not self.inited:
            self.init(output)
        
        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        start = req.start
        end = req.end or datetime.now()
        
        output(f"Querying bar data for {symbol}.{exchange.value} from {start} to {end} ({interval.value})")
        
        # Step 1: Load available data from cache
        cache_bars: List[BarData] = self.cache_backend.load_data(req)
        
        if cache_bars:
            cache_start = cache_bars[0].datetime
            cache_end = cache_bars[-1].datetime
            output(f"Loaded {len(cache_bars)} bars from cache ({cache_start} to {cache_end})")
        else:
            cache_start = None
            cache_end = None
            output("No data found in cache")
        
        # Step 2: Determine if we need to query from network
        need_network_query = False
        network_start = start
        network_end = end
        
        # Check if cache has complete data
        if not cache_bars or cache_start is None or cache_end is None:
            need_network_query = True
        else:
            # If cache completely covers the request range, no need for network query
            if cache_start <= start and cache_end >= end:
                need_network_query = False
            else:
                need_network_query = True
                # Calculate the missing date ranges
                if cache_start > start:
                    network_start = start
                else:
                    network_start = cache_end + timedelta(days=1)  # 从缓存结束日期的下一天开始获取
                
                if cache_end < end:
                    network_end = end
                else:
                    network_end = cache_start - timedelta(days=1)  # 只获取到缓存开始日期的前一天
        
        # Step 3: Query from network if needed
        net_bars = []
        if need_network_query:
            # Create request for network data
            net_req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=network_start,
                end=network_end
            )
            
            # Query from network datafeed
            output(f"Querying bars from network datafeed ({network_start} to {network_end})")
            net_bars = self.network_datafeed.query_bar_history(net_req, output)
            
            if net_bars:
                output(f"Received {len(net_bars)} bars from network datafeed")
                
                # Step 4: Async cache network data
                if len(net_bars) >= self.min_cache_length:
                    task = asyncio.create_task(self._async_cache_bars(net_bars, output))
                    self._cache_tasks.append(task)
                    task.add_done_callback(lambda t: self._cache_tasks.remove(t) if t in self._cache_tasks else None)
        
        # Step 5: Merge cache and network data
        if cache_bars and net_bars:
            # Merge the two datasets
            merged_bars = self._merge_bars(cache_bars, net_bars)
            output(f"Merged total {len(merged_bars)} bars")
            return merged_bars
        elif cache_bars:
            return cache_bars
        else:
            return net_bars
    
    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> List[TickData]:
        """
        Query tick history with cache support.
        Same logic as bar history query.
        """
        if not self.inited:
            self.init(output)
        
        symbol = req.symbol
        exchange = req.exchange
        start = req.start
        end = req.end or datetime.now()
        
        output(f"Querying tick data for {symbol}.{exchange.value} from {start} to {end}")
        
        # Step 1: Load available data from cache
        cache_ticks: List[TickData] = self.cache_backend.load_data(req)
        
        if cache_ticks:
            cache_start = cache_ticks[0].datetime
            cache_end = cache_ticks[-1].datetime
            output(f"Loaded {len(cache_ticks)} ticks from cache ({cache_start} to {cache_end})")
        else:
            cache_start = None
            cache_end = None
            output("No data found in cache")
        
        # Step 2: Determine if we need to query from network
        need_network_query = False
        network_start = start
        network_end = end
        
        # Check if cache has complete data
        if not cache_ticks or cache_start is None or cache_end is None:
            need_network_query = True
        else:
            # Check if start date is covered
            if cache_start > start:
                need_network_query = True
                network_start = start
            
            # Check if end date is covered
            if cache_end < end:
                need_network_query = True
                network_end = end
        
        # Step 3: Query from network if needed
        net_ticks = []
        if need_network_query:
            # Create request for network data
            net_req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                start=network_start,
                end=network_end
            )
            
            # Query from network datafeed
            output(f"Querying tick data from network datafeed ({network_start} to {network_end})")
            net_ticks = self.network_datafeed.query_tick_history(net_req, output)
            
            if net_ticks:
                output(f"Received {len(net_ticks)} ticks from network datafeed")
                
                # Step 4: Async cache network data
                if len(net_ticks) >= self.min_cache_length:
                    task = asyncio.create_task(self._async_cache_ticks(net_ticks, output))
                    self._cache_tasks.append(task)
                    task.add_done_callback(lambda t: self._cache_tasks.remove(t) if t in self._cache_tasks else None)
        
        # Step 5: Merge cache and network data
        if cache_ticks and net_ticks:
            # Merge the two datasets
            merged_ticks = self._merge_ticks(cache_ticks, net_ticks)
            output(f"Merged total {len(merged_ticks)} ticks")
            return merged_ticks
        elif cache_ticks:
            return cache_ticks
        else:
            return net_ticks
    
    async def _async_cache_bars(self, bars: List[BarData], output: Callable = print) -> bool:
        """
        Async cache bar data to backend.
        """
        try:
            output(f"Async caching {len(bars)} bars to cache backend")
            result = self.cache_backend.save_data(bars)
            if result:
                output(f"Successfully cached {len(bars)} bars")
            else:
                output(f"Failed to cache {len(bars)} bars")
            return result
        except Exception as e:
            output(f"Error caching bars: {e}")
            return False
    
    async def _async_cache_ticks(self, ticks: List[TickData], output: Callable = print) -> bool:
        """
        Async cache tick data to backend.
        """
        try:
            output(f"Async caching {len(ticks)} ticks to cache backend")
            result = self.cache_backend.save_data(ticks)
            if result:
                output(f"Successfully cached {len(ticks)} ticks")
            else:
                output(f"Failed to cache {len(ticks)} ticks")
            return result
        except Exception as e:
            output(f"Error caching ticks: {e}")
            return False
    
    def _merge_bars(self, cache_bars: List[BarData], net_bars: List[BarData]) -> List[BarData]:
        """
        Merge bars from cache and network, removing duplicates.
        """
        # Create a dictionary to store unique bars by datetime
        bar_dict = {}
        
        # Add cache bars first
        for bar in cache_bars:
            bar_dict[bar.datetime] = bar
        
        # Add network bars, overwriting cache bars with same datetime
        for bar in net_bars:
            bar_dict[bar.datetime] = bar
        
        # Convert back to sorted list
        return sorted(bar_dict.values(), key=lambda x: x.datetime)
    
    def _merge_ticks(self, cache_ticks: List[TickData], net_ticks: List[TickData]) -> List[TickData]:
        """
        Merge ticks from cache and network, removing duplicates.
        """
        # Create a dictionary to store unique ticks by datetime
        tick_dict = {}
        
        # Add cache ticks first
        for tick in cache_ticks:
            tick_dict[tick.datetime] = tick
        
        # Add network ticks, overwriting cache ticks with same datetime
        for tick in net_ticks:
            tick_dict[tick.datetime] = tick
        
        # Convert back to sorted list
        return sorted(tick_dict.values(), key=lambda x: x.datetime)
    
    async def wait_cache_tasks_complete(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all cache tasks to complete.
        
        Parameters:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if all tasks completed, False if timed out
        """
        if not self._cache_tasks:
            return True
        
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._cache_tasks, return_exceptions=True),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            return False
    
    def cancel_cache_tasks(self) -> None:
        """
        Cancel all pending cache tasks.
        """
        for task in self._cache_tasks:
            if not task.done():
                task.cancel()
        self._cache_tasks.clear()


# Factory function to create cached datafeed
T = TypeVar('T', BarData, TickData)  # Re-declare for function scope
def create_cached_datafeed(network_datafeed: BaseDatafeed, cache_backend: Optional[BaseCacheBackend[T]] = None) -> CachedDatafeedWrapper:
    """
    Create a cached datafeed wrapper around a network datafeed.
    
    Parameters:
        network_datafeed: The network datafeed to wrap
        cache_backend: The cache backend to use (default: ParquetCacheBackend)
        
    Returns:
        CachedDatafeedWrapper: The wrapped datafeed with caching support
    """
    return CachedDatafeedWrapper(network_datafeed, cache_backend)