#!/usr/bin/env python3
"""
Test script to verify ParquetCacheBackend is now the default cache backend.
"""

import asyncio
from datetime import datetime, timedelta
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.setting import SETTINGS
from vnpy.trader.cached_datafeed import create_cached_datafeed, CachedDatafeedWrapper
from vnpy.trader.object import HistoryRequest, BarData, TickData
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.parquet_cache_backend import ParquetCacheBackend
from vnpy.trader.cached_datafeed import DatabaseCacheBackend


class MockNetworkDatafeed:
    """
    Mock network datafeed for testing.
    """
    
    def init(self, output=print):
        output("Mock network datafeed initialized")
        return True
    
    def query_bar_history(self, req: HistoryRequest, output=print):
        """
        Simulate bar data retrieval.
        """
        output(f"Mock: Querying bars from network...")
        
        # Generate mock bars
        bars = []
        current_date = req.start.date()
        end_date = req.end.date()
        
        while current_date <= end_date:
            bar = BarData(
                symbol=req.symbol,
                exchange=req.exchange,
                datetime=datetime.combine(current_date, datetime.min.time()),
                interval=req.interval,
                open_price=10.0,
                high_price=12.0,
                low_price=9.0,
                close_price=11.0,
                volume=1000,
                turnover=11000.0,
                open_interest=0,
                gateway_name="MOCK"
            )
            bars.append(bar)
            current_date += timedelta(days=1)
        
        output(f"Mock: Returned {len(bars)} bars")
        return bars
    
    def query_tick_history(self, req: HistoryRequest, output=print):
        """
        Simulate tick data retrieval.
        """
        output(f"Mock: Querying ticks from network...")
        
        # Generate mock ticks
        ticks = []
        current_time = req.start
        end_time = req.end
        
        while current_time < end_time:
            tick = TickData(
                symbol=req.symbol,
                exchange=req.exchange,
                datetime=current_time,
                last_price=10.5,
                volume=100,
                turnover=1050.0,
                open_interest=0,
                bid_price_1=10.4,
                bid_volume_1=10,
                ask_price_1=10.6,
                ask_volume_1=10,
                gateway_name="MOCK"
            )
            ticks.append(tick)
            current_time += timedelta(seconds=10)
        
        output(f"Mock: Returned {len(ticks)} ticks")
        return ticks


async def test_default_cache_backend():
    """
    Test that ParquetCacheBackend is now the default cache backend.
    """
    print("=" * 80)
    print("Test: Default Cache Backend")
    print("=" * 80)
    
    # Create mock network datafeed
    mock_network = MockNetworkDatafeed()
    
    # Test 1: Create cached datafeed without specifying backend
    print("\nTest 1: Creating cached datafeed without specifying backend")
    cached_datafeed = create_cached_datafeed(mock_network)
    
    # Check the type of cache_backend
    backend_type = type(cached_datafeed.cache_backend).__name__
    print(f"Cache backend type: {backend_type}")
    
    # Verify it's ParquetCacheBackend
    if backend_type == "ParquetCacheBackend":
        print("✓ SUCCESS: Default cache backend is now ParquetCacheBackend")
    else:
        print("✗ FAILURE: Default cache backend is not ParquetCacheBackend")
        return False
    
    # Test 2: Create cached datafeed with explicit Parquet backend
    print("\nTest 2: Creating cached datafeed with explicit Parquet backend")
    parquet_backend = ParquetCacheBackend(cache_root="./test_parquet_cache")
    cached_datafeed2 = create_cached_datafeed(mock_network, parquet_backend)
    
    backend_type2 = type(cached_datafeed2.cache_backend).__name__
    print(f"Cache backend type: {backend_type2}")
    
    if backend_type2 == "ParquetCacheBackend":
        print("✓ SUCCESS: Explicit Parquet backend works correctly")
    else:
        print("✗ FAILURE: Explicit Parquet backend failed")
        return False
    
    # Test 3: Create cached datafeed with explicit Database backend (backward compatibility)
    print("\nTest 3: Creating cached datafeed with explicit Database backend")
    try:
        db_backend = DatabaseCacheBackend()
        cached_datafeed3 = create_cached_datafeed(mock_network, db_backend)
        
        backend_type3 = type(cached_datafeed3.cache_backend).__name__
        print(f"Cache backend type: {backend_type3}")
        
        if backend_type3 == "DatabaseCacheBackend":
            print("✓ SUCCESS: Explicit Database backend still works (backward compatibility)")
        else:
            print("✗ FAILURE: Explicit Database backend failed")
            return False
    except Exception as e:
        print(f"✗ FAILURE: Database backend initialization failed: {e}")
        return False
    
    # Test 4: Verify the default cache backend works in practice
    print("\nTest 4: Testing default cache backend functionality")
    cached_datafeed.init(print)
    
    # Create test request
    req = HistoryRequest(
        symbol="TEST",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime.now() - timedelta(days=5),
        end=datetime.now()
    )
    
    try:
        bars = cached_datafeed.query_bar_history(req, print)
        print(f"✓ SUCCESS: Bar query returned {len(bars)} bars")
        
        # Wait for async cache to complete
        await cached_datafeed.wait_cache_tasks_complete(timeout=5.0)
        print(f"✓ SUCCESS: Async cache operation completed")
        
    except Exception as e:
        print(f"✗ FAILURE: Cache backend functionality test failed: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("All tests passed! Default cache backend is now ParquetCacheBackend")
    print("=" * 80)
    return True


async def main():
    """
    Run the test.
    """
    await test_default_cache_backend()


if __name__ == "__main__":
    asyncio.run(main())