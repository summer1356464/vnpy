#!/usr/bin/env python3
"""
Example demonstrating the new cached datafeed architecture.
"""

from datetime import datetime, timedelta
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.setting import SETTINGS
from vnpy.trader.cached_datafeed import create_cached_datafeed, DatabaseCacheBackend
from vnpy.trader.parquet_cache_backend import ParquetCacheBackend
from vnpy.trader.object import HistoryRequest
from vnpy.trader.constant import Interval, Exchange


def example_default_caching():
    """
    Example 1: Using default caching (database backend)
    """
    print("=" * 80)
    print("Example 1: Using default caching (database backend)")
    print("=" * 80)
    
    # Enable caching in settings
    SETTINGS["datafeed.use_cache"] = True
    
    # Get datafeed (will be wrapped with cache automatically)
    datafeed = get_datafeed()
    datafeed.init(print)
    
    # Create test request
    req = HistoryRequest(
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime.now() - timedelta(days=30),
        end=datetime.now()
    )
    
    # Query data (will use cache if available)
    bars = datafeed.query_bar_history(req, print)
    print(f"Received {len(bars)} bars\n")


def example_manual_wrapping():
    """
    Example 2: Manually wrapping a datafeed with cache
    """
    print("=" * 80)
    print("Example 2: Manually wrapping a datafeed with cache")
    print("=" * 80)
    
    # Get the raw network datafeed
    SETTINGS["datafeed.use_cache"] = False  # Disable automatic caching
    raw_datafeed = get_datafeed()
    
    # Create database cache backend
    db_cache_backend = DatabaseCacheBackend()
    
    # Manually wrap the datafeed
    from vnpy.trader.cached_datafeed import create_cached_datafeed
    cached_datafeed = create_cached_datafeed(raw_datafeed, db_cache_backend)
    cached_datafeed.init(print)
    
    # Create test request
    req = HistoryRequest(
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime.now() - timedelta(days=30),
        end=datetime.now()
    )
    
    # Query data
    bars = cached_datafeed.query_bar_history(req, print)
    print(f"Received {len(bars)} bars\n")


def example_parquet_caching():
    """
    Example 3: Using parquet file cache backend
    """
    print("=" * 80)
    print("Example 3: Using parquet file cache backend")
    print("=" * 80)
    
    try:
        # Get the raw network datafeed
        SETTINGS["datafeed.use_cache"] = False  # Disable automatic caching
        raw_datafeed = get_datafeed()
        
        # Create parquet cache backend
        parquet_cache_backend = ParquetCacheBackend(cache_root="./parquet_cache")
        
        # Wrap the datafeed with parquet cache
        from vnpy.trader.cached_datafeed import create_cached_datafeed
        cached_datafeed = create_cached_datafeed(raw_datafeed, parquet_cache_backend)
        cached_datafeed.init(print)
        
        # Create test request
        req = HistoryRequest(
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=datetime.now() - timedelta(days=30),
            end=datetime.now()
        )
        
        # Query data
        bars = cached_datafeed.query_bar_history(req, print)
        print(f"Received {len(bars)} bars")
        print(f"Parquet cache files saved in: {parquet_cache_backend.cache_root}\n")
    except ImportError as e:
        print(f"Parquet caching requires pandas and pyarrow: {e}")
        print("Install with: pip install pandas pyarrow\n")


def example_direct_db_cache_module():
    """
    Example 4: Using the independent direct_db_cache module
    """
    print("=" * 80)
    print("Example 4: Using the independent direct_db_cache module")
    print("=" * 80)
    
    try:
        # Import the independent module
        from vnpy_directdb_cache.direct_db_cached_datafeed import DirectDBCachedDatafeed, get_direct_db_cached_datafeed
        
        # Get the raw network datafeed
        SETTINGS["datafeed.use_cache"] = False
        raw_datafeed = get_datafeed()
        
        # Create direct DB cached datafeed
        direct_db_cached = DirectDBCachedDatafeed(network_datafeed=raw_datafeed)
        direct_db_cached.init(print)
        
        # Create test request
        req = HistoryRequest(
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=datetime.now() - timedelta(days=30),
            end=datetime.now()
        )
        
        # Query data
        bars = direct_db_cached.query_bar_history(req, print)
        print(f"Received {len(bars)} bars\n")
    except ImportError as e:
        print(f"Direct DB cache module not available: {e}")
        print("Install with: pip install -e ./vnpy_directdb_cache\n")


if __name__ == "__main__":
    # Run all examples
    example_default_caching()
    example_manual_wrapping()
    example_parquet_caching()
    example_direct_db_cache_module()
    
    print("=" * 80)
    print("All examples completed!")
    print("=" * 80)