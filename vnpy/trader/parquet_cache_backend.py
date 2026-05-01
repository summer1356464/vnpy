from typing import List, Optional
from datetime import datetime
import os
import pandas as pd
from pathlib import Path

from .object import HistoryRequest, BarData, TickData
from .constant import Interval, Exchange
from .cache_backend import BaseCacheBackend, T


class ParquetCacheBackend(BaseCacheBackend[T]):
    """
    Parquet file cache backend implementation.
    Stores data in parquet format with a directory structure like:
    cache_root/
        symbol_exchange/
            bar/interval/
                YYYY-MM-DD.parquet
            tick/
                YYYY-MM-DD.parquet
    """
    
    def __init__(self, cache_root: str = "./data_cache"):
        """
        Initialize parquet cache backend.
        
        Parameters:
            cache_root: Root directory for cache files
        """
        self.cache_root = Path(cache_root)
        self.cache_root.mkdir(exist_ok=True, parents=True)
    
    def init(self) -> bool:
        """
        Initialize the parquet cache backend.
        """
        self.cache_root.mkdir(exist_ok=True, parents=True)
        return True
    
    def _get_symbol_dir(self, symbol: str, exchange: Exchange) -> Path:
        """
        Get directory path for a specific symbol and exchange.
        """
        symbol_key = f"{symbol}_{exchange.value}"
        return self.cache_root / symbol_key
    
    def _get_data_dir(self, symbol: str, exchange: Exchange, data_type: str, interval: Optional[Interval] = None) -> Path:
        """
        Get directory path for specific data type and interval.
        """
        symbol_dir = self._get_symbol_dir(symbol, exchange)
        if data_type == "bar":
            return symbol_dir / "bar" / interval.value if interval else symbol_dir / "bar"
        else:  # tick
            return symbol_dir / "tick"
    
    def _get_file_path(self, symbol: str, exchange: Exchange, data_type: str, date: datetime, interval: Optional[Interval] = None) -> Path:
        """
        Get parquet file path for specific date.
        """
        data_dir = self._get_data_dir(symbol, exchange, data_type, interval)
        data_dir.mkdir(exist_ok=True, parents=True)
        file_name = f"{date.strftime('%Y-%m-%d')}.parquet"
        return data_dir / file_name
    
    def _bar_to_df(self, bars: List[BarData]) -> pd.DataFrame:
        """
        Convert BarData list to pandas DataFrame.
        """
        if not bars:
            return pd.DataFrame()
        
        data = {
            "datetime": [bar.datetime for bar in bars],
            "symbol": [bar.symbol for bar in bars],
            "exchange": [bar.exchange.value for bar in bars],
            "interval": [bar.interval.value for bar in bars],
            "open_price": [bar.open_price for bar in bars],
            "high_price": [bar.high_price for bar in bars],
            "low_price": [bar.low_price for bar in bars],
            "close_price": [bar.close_price for bar in bars],
            "volume": [bar.volume for bar in bars],
            "turnover": [bar.turnover for bar in bars],
            "open_interest": [bar.open_interest for bar in bars]
        }
        
        df = pd.DataFrame(data)
        df["datetime"] = pd.to_datetime(df["datetime"])
        return df
    
    def _df_to_bar(self, df: pd.DataFrame) -> List[BarData]:
        """
        Convert pandas DataFrame to BarData list.
        """
        bars = []
        for _, row in df.iterrows():
            bar = BarData(
                symbol=row["symbol"],
                exchange=Exchange(row["exchange"]),
                datetime=row["datetime"],
                interval=Interval(row["interval"]),
                open_price=row["open_price"],
                high_price=row["high_price"],
                low_price=row["low_price"],
                close_price=row["close_price"],
                volume=row["volume"],
                turnover=row["turnover"],
                open_interest=row["open_interest"],
                gateway_name="PARQUET_CACHE"
            )
            bars.append(bar)
        return bars
    
    def _tick_to_df(self, ticks: List[TickData]) -> pd.DataFrame:
        """
        Convert TickData list to pandas DataFrame.
        """
        if not ticks:
            return pd.DataFrame()
        
        data = {
            "datetime": [tick.datetime for tick in ticks],
            "symbol": [tick.symbol for tick in ticks],
            "exchange": [tick.exchange.value for tick in ticks],
            "last_price": [tick.last_price for tick in ticks],
            "volume": [tick.volume for tick in ticks],
            "turnover": [tick.turnover for tick in ticks],
            "open_interest": [tick.open_interest for tick in ticks],
            "bid_price_1": [tick.bid_price_1 for tick in ticks],
            "bid_volume_1": [tick.bid_volume_1 for tick in ticks],
            "ask_price_1": [tick.ask_price_1 for tick in ticks],
            "ask_volume_1": [tick.ask_volume_1 for tick in ticks]
        }
        
        df = pd.DataFrame(data)
        df["datetime"] = pd.to_datetime(df["datetime"])
        return df
    
    def _df_to_tick(self, df: pd.DataFrame) -> List[TickData]:
        """
        Convert pandas DataFrame to TickData list.
        """
        ticks = []
        for _, row in df.iterrows():
            tick = TickData(
                symbol=row["symbol"],
                exchange=Exchange(row["exchange"]),
                datetime=row["datetime"],
                last_price=row["last_price"],
                volume=row["volume"],
                turnover=row["turnover"],
                open_interest=row["open_interest"],
                bid_price_1=row["bid_price_1"],
                bid_volume_1=row["bid_volume_1"],
                ask_price_1=row["ask_price_1"],
                ask_volume_1=row["ask_volume_1"],
                gateway_name="PARQUET_CACHE"
            )
            ticks.append(tick)
        return ticks
    
    def load_data(self, req: HistoryRequest) -> List[T]:
        """
        Load data from parquet cache files.
        """
        symbol = req.symbol
        exchange = req.exchange
        start = req.start
        end = req.end or datetime.now()
        
        if isinstance(req.interval, Interval):
            # Bar data
            data_type = "bar"
            interval = req.interval
            data_dir = self._get_data_dir(symbol, exchange, data_type, interval)
        else:
            # Tick data
            data_type = "tick"
            interval = None
            data_dir = self._get_data_dir(symbol, exchange, data_type)
        
        if not data_dir.exists():
            return []
        
        # Find all parquet files in date range
        files = []
        current_date = start.date()
        end_date = end.date()
        
        while current_date <= end_date:
            file_path = self._get_file_path(symbol, exchange, data_type, current_date, interval)
            if file_path.exists():
                files.append(file_path)
            current_date += pd.Timedelta(days=1)
        
        if not files:
            return []
        
        # Read and concatenate all files
        dfs = []
        for file_path in files:
            df = pd.read_parquet(file_path)
            dfs.append(df)
        
        if not dfs:
            return []
        
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Filter by datetime range
        combined_df = combined_df[(combined_df["datetime"] >= start) & (combined_df["datetime"] <= end)]
        
        # Convert back to data objects
        if data_type == "bar":
            return self._df_to_bar(combined_df)
        else:
            return self._df_to_tick(combined_df)
    
    def save_data(self, data: List[T]) -> bool:
        """
        Save data to parquet cache files.
        """
        if not data:
            return False
        
        try:
            if isinstance(data[0], BarData):
                # Bar data
                data_type = "bar"
                df = self._bar_to_df(data)
                
                # Group by date and save to separate files
                df["date"] = df["datetime"].dt.date
                
                for date, date_df in df.groupby("date"):
                    interval = data[0].interval
                    file_path = self._get_file_path(data[0].symbol, data[0].exchange, data_type, date, interval)
                    
                    # Append if file exists, otherwise create new
                    if file_path.exists():
                        existing_df = pd.read_parquet(file_path)
                        combined_df = pd.concat([existing_df, date_df.drop(columns=["date"])], ignore_index=True)
                        # Remove duplicates
                        combined_df = combined_df.drop_duplicates(subset=["datetime"])
                        combined_df.to_parquet(file_path, index=False, compression="snappy")
                    else:
                        date_df.drop(columns=["date"]).to_parquet(file_path, index=False, compression="snappy")
                        
            elif isinstance(data[0], TickData):
                # Tick data
                data_type = "tick"
                df = self._tick_to_df(data)
                
                # Group by date and save to separate files
                df["date"] = df["datetime"].dt.date
                
                for date, date_df in df.groupby("date"):
                    file_path = self._get_file_path(data[0].symbol, data[0].exchange, data_type, date)
                    
                    # Append if file exists, otherwise create new
                    if file_path.exists():
                        existing_df = pd.read_parquet(file_path)
                        combined_df = pd.concat([existing_df, date_df.drop(columns=["date"])], ignore_index=True)
                        # Remove duplicates
                        combined_df = combined_df.drop_duplicates(subset=["datetime"])
                        combined_df.to_parquet(file_path, index=False, compression="snappy")
                    else:
                        date_df.drop(columns=["date"]).to_parquet(file_path, index=False, compression="snappy")
                        
            return True
        except Exception as e:
            print(f"Error saving data to parquet: {e}")
            return False