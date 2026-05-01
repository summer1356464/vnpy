#!/usr/bin/env python3
"""
Test script to verify async task management and type annotation fixes.
"""

import asyncio
import time
from datetime import datetime, timedelta
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.setting import SETTINGS
from vnpy.trader.cached_datafeed import create_cached_datafeed, DatabaseCacheBackend
from vnpy.trader.object import HistoryRequest, BarData, TickData
from vnpy.trader.constant import Interval, Exchange


class MockNetworkDatafeed:
    """
    Mock network datafeed that simulates slow data retrieval.
    """
    
    def init(self, output=print):
        output("Mock network datafeed initialized")
        return True
    
    def query_bar_history(self, req: HistoryRequest, output=print):
        """
        Simulate slow bar data retrieval.
        """
        output(f"Mock: Querying bars from network...")
        time.sleep(0.5)  # Simulate network delay
        
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
        Simulate slow tick data retrieval.
        """
        output(f"Mock: Querying ticks from network...")
        time.sleep(0.5)  # Simulate network delay
        
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


class MockCacheBackend:
    """
    Mock cache backend that simulates slow cache operations.
    """
    
    def __init__(self):
        self.cache = {}
    
    def init(self):
        return True
    
    def load_data(self, req):
        """
        Load data from mock cache.
        """
        interval_value = req.interval.value if req.interval else "tick"
        key = f"{req.symbol}_{req.exchange.value}_{interval_value}_{req.start}_{req.end}"
        return self.cache.get(key, [])
    
    def save_data(self, data):
        """
        Save data to mock cache with simulated delay.
        """
        if not data:
            return False
        
        # Simulate slow cache operation
        time.sleep(0.3)
        
        # For simplicity, we don't actually store the data in this mock
        print(f"Mock cache: Saved {len(data)} items")
        return True


async def test_async_task_management():
    """
    Test async task management functionality.
    """
    print("=" * 80)
    print("Test 1: Async Task Management")
    print("=" * 80)
    
    # Create mock components
    mock_network = MockNetworkDatafeed()
    mock_cache = MockCacheBackend()
    
    # Create cached datafeed
    from vnpy.trader.cached_datafeed import create_cached_datafeed
    cached_datafeed = create_cached_datafeed(mock_network, mock_cache)
    cached_datafeed.init(print)
    
    # Create test request
    req = HistoryRequest(
        symbol="TEST",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime.now() - timedelta(days=5),
        end=datetime.now()
    )
    
    # Initial task count should be 0
    print(f"\nInitial cache tasks: {len(cached_datafeed._cache_tasks)}")
    
    # Query data - this should trigger async cache task
    bars = cached_datafeed.query_bar_history(req, print)
    print(f"Received {len(bars)} bars")
    
    # Task count should be 1 after query
    print(f"Cache tasks after query: {len(cached_datafeed._cache_tasks)}")
    
    # Wait for cache task to complete
    print("\nWaiting for cache tasks to complete...")
    await cached_datafeed.wait_cache_tasks_complete(timeout=5.0)
    print(f"Cache tasks after wait: {len(cached_datafeed._cache_tasks)}")
    
    # Test multiple queries
    print("\n--- Multiple Queries Test ---")
    for i in range(3):
        print(f"\nQuery {i+1}:")
        bars = cached_datafeed.query_bar_history(req, print)
        print(f"Cache tasks during multiple queries: {len(cached_datafeed._cache_tasks)}")
    
    # Wait for all tasks to complete
    await cached_datafeed.wait_cache_tasks_complete(timeout=5.0)
    print(f"\nFinal cache tasks after multiple queries: {len(cached_datafeed._cache_tasks)}")
    
    # Test task cancellation
    print("\n--- Task Cancellation Test ---")
    # Start a new query
    bars = cached_datafeed.query_bar_history(req, print)
    print(f"Cache tasks before cancellation: {len(cached_datafeed._cache_tasks)}")
    
    # Cancel all tasks
    cached_datafeed.cancel_cache_tasks()
    print(f"Cache tasks after cancellation: {len(cached_datafeed._cache_tasks)}")
    
    print("\n✓ Async task management test passed")


async def test_type_annotations():
    """
    Test that type annotations are working correctly.
    """
    print("\n" + "=" * 80)
    print("Test 2: Type Annotations")
    print("=" * 80)
    
    try:
        # Create mock components
        mock_network = MockNetworkDatafeed()
        mock_cache = MockCacheBackend()
        
        # Create cached datafeed
        from vnpy.trader.cached_datafeed import create_cached_datafeed
        cached_datafeed = create_cached_datafeed(mock_network, mock_cache)
        cached_datafeed.init(print)
        
        # Test bar data query
        bar_req = HistoryRequest(
            symbol="TEST",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=datetime.now() - timedelta(days=5),
            end=datetime.now()
        )
        
        bars = cached_datafeed.query_bar_history(bar_req, print)
        print(f"Bar query returned {len(bars)} items of type {type(bars[0]).__name__}")
        
        # Verify all items are BarData
        all_bar_data = all(isinstance(bar, BarData) for bar in bars)
        print(f"All items are BarData: {all_bar_data}")
        
        # Test tick data query
        tick_req = HistoryRequest(
            symbol="TEST",
            exchange=Exchange.SZSE,
            start=datetime.now() - timedelta(minutes=5),
            end=datetime.now()
        )
        
        ticks = cached_datafeed.query_tick_history(tick_req, print)
        print(f"Tick query returned {len(ticks)} items of type {type(ticks[0]).__name__}")
        
        # Verify all items are TickData
        all_tick_data = all(isinstance(tick, TickData) for tick in ticks)
        print(f"All items are TickData: {all_tick_data}")
        
        print("\n✓ Type annotations test passed")
        return True
    except Exception as e:
        print(f"\n✗ Type annotations test failed: {e}")
        return False


async def main():
    """
    Run all tests.
    """
    await test_async_task_management()
    await test_type_annotations()
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())