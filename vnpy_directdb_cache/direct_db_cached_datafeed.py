from typing import List, Optional, Callable
from datetime import datetime, timedelta

from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.database import get_database
from vnpy.trader.object import HistoryRequest, BarData, TickData
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.locale import _


class DirectDBCachedDatafeed(BaseDatafeed):
    """
    Datafeed with local database caching support.
    Priority: Local database → Network datafeed
    Automatically caches network data to local database.
    """
    
    def __init__(self, network_datafeed: Optional[BaseDatafeed] = None):
        """
        Initialize cached datafeed with the given network datafeed.
        
        Parameters:
            network_datafeed: The network datafeed to use for fallback queries
        """
        self.network_datafeed = network_datafeed
        self.database = get_database()
        self.inited = False
        
        # Cache settings
        self.min_cache_length = 10  # Minimum number of bars/ticks to cache
    
    def init(self, output: Callable = print) -> bool:
        """
        Initialize both network datafeed and database.
        """
        output(_("Initializing direct DB cached datafeed..."))
        
        # Initialize network datafeed if provided
        if self.network_datafeed:
            if hasattr(self.network_datafeed, 'init'):
                network_init = self.network_datafeed.init(output)
                if not network_init:
                    output(_("Warning: Network datafeed initialization failed, will use database only"))
        
        self.inited = True
        output(_("Direct DB cached datafeed initialized successfully"))
        return True
    
    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> List[BarData]:
        """
        Query bar history with cache support.
        1. First try to load from local database
        2. If database doesn't have complete data, query from network datafeed
        3. Merge and cache the network data to local database
        """
        if not self.inited:
            self.init(output)
        
        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        start = req.start
        end = req.end or datetime.now()
        
        output(f"Querying bar data for {symbol}.{exchange.value} from {start} to {end} ({interval.value})")
        
        # Step 1: Load available data from local database
        db_bars = self.database.load_bar_data(symbol, exchange, interval, start, end)
        
        if db_bars:
            db_start = db_bars[0].datetime
            db_end = db_bars[-1].datetime
            output(f"Loaded {len(db_bars)} bars from local database ({db_start} to {db_end})")
        else:
            db_start = None  # No data in database
            db_end = None  # No data in database
            output("No data found in local database")
        
        # Step 2: Determine if we need to query from network
        need_network_query = False
        network_start = start
        network_end = end
        
        # Check if database has complete data
        if not db_bars or db_start is None or db_end is None:
            need_network_query = True
        else:
            # Check if start date is covered
            if db_start > start:
                need_network_query = True
                network_start = start
            
            # Check if end date is covered
            if db_end < end:
                need_network_query = True
                network_end = end
        
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
                
                # Step 4: Cache network data to local database
                self._cache_bars(net_bars, output)
        
        # Step 5: Merge database and network data
        if db_bars and net_bars:
            # Merge the two datasets
            merged_bars = self._merge_bars(db_bars, net_bars)
            output(f"Merged total {len(merged_bars)} bars")
            return merged_bars
        elif db_bars:
            return db_bars
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
        
        # Step 1: Load available data from local database
        db_ticks = self.database.load_tick_data(symbol, exchange, start, end)
        
        if db_ticks:
            db_start = db_ticks[0].datetime
            db_end = db_ticks[-1].datetime
            output(f"Loaded {len(db_ticks)} ticks from local database ({db_start} to {db_end})")
        else:
            db_start = None  # No data in database
            db_end = None  # No data in database
            output("No data found in local database")
        
        # Step 2: Determine if we need to query from network
        need_network_query = False
        network_start = start
        network_end = end
        
        # Check if database has complete data
        if not db_ticks or db_start is None or db_end is None:
            need_network_query = True
        else:
            # Check if start date is covered
            if db_start > start:
                need_network_query = True
                network_start = start
            
            # Check if end date is covered
            if db_end < end:
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
                
                # Step 4: Cache network data to local database
                self._cache_ticks(net_ticks, output)
        
        # Step 5: Merge database and network data
        if db_ticks and net_ticks:
            # Merge the two datasets
            merged_ticks = self._merge_ticks(db_ticks, net_ticks)
            output(f"Merged total {len(merged_ticks)} ticks")
            return merged_ticks
        elif db_ticks:
            return db_ticks
        else:
            return net_ticks
    
    def _cache_bars(self, bars: List[BarData], output: Callable = print) -> bool:
        """
        Cache bar data to local database.
        """
        if not bars:
            return False
            
        # Cache all valid data (history data is unique, no expiry needed)
        if len(bars) < self.min_cache_length:
            output(f"Skipping cache: only {len(bars)} bars (min: {self.min_cache_length})")
            return False
        
        output(f"Caching {len(bars)} bars to local database")
        return self.database.save_bar_data(bars)
    
    def _cache_ticks(self, ticks: List[TickData], output: Callable = print) -> bool:
        """
        Cache tick data to local database.
        """
        if not ticks:
            return False
            
        # Cache all valid data (history data is unique, no expiry needed)
        if len(ticks) < self.min_cache_length:
            output(f"Skipping cache: only {len(ticks)} ticks (min: {self.min_cache_length})")
            return False
        
        output(f"Caching {len(ticks)} ticks to local database")
        return self.database.save_tick_data(ticks)
    
    def _merge_bars(self, db_bars: List[BarData], net_bars: List[BarData]) -> List[BarData]:
        """
        Merge bars from database and network, removing duplicates.
        """
        # Create a dictionary to store unique bars by datetime
        bar_dict = {}
        
        # Add database bars first
        for bar in db_bars:
            bar_dict[bar.datetime] = bar
        
        # Add network bars, overwriting database bars with same datetime
        for bar in net_bars:
            bar_dict[bar.datetime] = bar
        
        # Convert back to sorted list
        return sorted(bar_dict.values(), key=lambda x: x.datetime)
    
    def _merge_ticks(self, db_ticks: List[TickData], net_ticks: List[TickData]) -> List[TickData]:
        """
        Merge ticks from database and network, removing duplicates.
        """
        # Create a dictionary to store unique ticks by datetime
        tick_dict = {}
        
        # Add database ticks first
        for tick in db_ticks:
            tick_dict[tick.datetime] = tick
        
        # Add network ticks, overwriting database ticks with same datetime
        for tick in net_ticks:
            tick_dict[tick.datetime] = tick
        
        # Convert back to sorted list
        return sorted(tick_dict.values(), key=lambda x: x.datetime)


# Global direct DB cached datafeed instance
direct_db_cached_datafeed: Optional[DirectDBCachedDatafeed] = None


def get_direct_db_cached_datafeed() -> DirectDBCachedDatafeed:
    """
    Get the global direct DB cached datafeed instance.
    """
    global direct_db_cached_datafeed
    if not direct_db_cached_datafeed:
        direct_db_cached_datafeed = DirectDBCachedDatafeed()
    return direct_db_cached_datafeed