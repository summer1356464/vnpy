import sqlite3
import os
from datetime import datetime
from typing import List, Union

from vnpy.trader.database import BaseDatabase, BarOverview, TickOverview, convert_tz
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.setting import SETTINGS


class Database(BaseDatabase):
    """
    SQLite database implementation for VNPY.
    """
    
    def __init__(self):
        self.db_path: str = SETTINGS.get("database.path", "database.db")
        self.conn: Union[sqlite3.Connection, None] = None
        
        self.init_db()
    
    def init_db(self):
        # Create database directory if not exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # Connect to database
        self.conn = sqlite3.connect(
            self.db_path, 
            check_same_thread=False,  # Allow multi-thread access
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        
        # Create cursor
        cursor = self.conn.cursor()
        
        # Create bar data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bar_data (
                symbol TEXT,
                exchange TEXT,
                datetime TIMESTAMP,
                interval TEXT,
                volume INTEGER,
                turnover FLOAT,
                open_interest INTEGER,
                open_price FLOAT,
                high_price FLOAT,
                low_price FLOAT,
                close_price FLOAT,
                PRIMARY KEY (symbol, exchange, datetime, interval)
            )
        """)
        
        # Create tick data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tick_data (
                symbol TEXT,
                exchange TEXT,
                datetime TIMESTAMP,
                name TEXT,
                volume INTEGER,
                turnover FLOAT,
                open_interest INTEGER,
                last_price FLOAT,
                last_volume INTEGER,
                limit_up FLOAT,
                limit_down FLOAT,
                open_price FLOAT,
                high_price FLOAT,
                low_price FLOAT,
                pre_close FLOAT,
                bid_price_1 FLOAT,
                bid_volume_1 INTEGER,
                ask_price_1 FLOAT,
                ask_volume_1 INTEGER,
                bid_price_2 FLOAT,
                bid_volume_2 INTEGER,
                ask_price_2 FLOAT,
                ask_volume_2 INTEGER,
                bid_price_3 FLOAT,
                bid_volume_3 INTEGER,
                ask_price_3 FLOAT,
                ask_volume_3 INTEGER,
                bid_price_4 FLOAT,
                bid_volume_4 INTEGER,
                ask_price_4 FLOAT,
                ask_volume_4 INTEGER,
                bid_price_5 FLOAT,
                bid_volume_5 INTEGER,
                ask_price_5 FLOAT,
                ask_volume_5 INTEGER,
                PRIMARY KEY (symbol, exchange, datetime)
            )
        """)
        
        # Create index for bar data query
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bar_data_symbol_exchange_interval ON bar_data (symbol, exchange, interval)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bar_data_datetime ON bar_data (datetime)
        """)
        
        # Create index for tick data query
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tick_data_symbol_exchange ON tick_data (symbol, exchange)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tick_data_datetime ON tick_data (datetime)
        """)
        
        # Commit changes
        self.conn.commit()
    
    def save_bar_data(self, bars: List[BarData], stream: bool = False) -> bool:
        if not bars:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            for bar in bars:
                # Convert datetime timezone
                dt = convert_tz(bar.datetime)
                
                # Insert or replace bar data
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO bar_data 
                    (symbol, exchange, datetime, interval, volume, turnover, open_interest, 
                     open_price, high_price, low_price, close_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bar.symbol,
                        bar.exchange.value,
                        dt,
                        bar.interval.value,
                        bar.volume,
                        bar.turnover,
                        bar.open_interest,
                        bar.open_price,
                        bar.high_price,
                        bar.low_price,
                        bar.close_price
                    )
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Save bar data failed: {e}")
            return False
    
    def save_tick_data(self, ticks: List[TickData], stream: bool = False) -> bool:
        if not ticks:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            for tick in ticks:
                # Convert datetime timezone
                dt = convert_tz(tick.datetime)
                
                # Insert or replace tick data
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tick_data 
                    (symbol, exchange, datetime, name, volume, turnover, open_interest, 
                     last_price, last_volume, limit_up, limit_down, open_price, 
                     high_price, low_price, pre_close, bid_price_1, bid_volume_1, 
                     ask_price_1, ask_volume_1, bid_price_2, bid_volume_2, ask_price_2, 
                     ask_volume_2, bid_price_3, bid_volume_3, ask_price_3, ask_volume_3, 
                     bid_price_4, bid_volume_4, ask_price_4, ask_volume_4, bid_price_5, 
                     bid_volume_5, ask_price_5, ask_volume_5)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tick.symbol,
                        tick.exchange.value,
                        dt,
                        tick.name,
                        tick.volume,
                        tick.turnover,
                        tick.open_interest,
                        tick.last_price,
                        tick.last_volume,
                        tick.limit_up,
                        tick.limit_down,
                        tick.open_price,
                        tick.high_price,
                        tick.low_price,
                        tick.pre_close,
                        tick.bid_price_1,
                        tick.bid_volume_1,
                        tick.ask_price_1,
                        tick.ask_volume_1,
                        tick.bid_price_2,
                        tick.bid_volume_2,
                        tick.ask_price_2,
                        tick.ask_volume_2,
                        tick.bid_price_3,
                        tick.bid_volume_3,
                        tick.ask_price_3,
                        tick.ask_volume_3,
                        tick.bid_price_4,
                        tick.bid_volume_4,
                        tick.ask_price_4,
                        tick.ask_volume_4,
                        tick.bid_price_5,
                        tick.bid_volume_5,
                        tick.ask_price_5,
                        tick.ask_volume_5
                    )
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Save tick data failed: {e}")
            return False
    
    def load_bar_data(
        self, 
        symbol: str, 
        exchange: Exchange, 
        interval: Interval, 
        start: datetime, 
        end: datetime
    ) -> List[BarData]:
        bars: List[BarData] = []
        
        try:
            cursor = self.conn.cursor()
            
            # Convert datetime timezone
            start = convert_tz(start)
            end = convert_tz(end)
            
            # Query bar data
            cursor.execute(
                """
                SELECT * FROM bar_data 
                WHERE symbol = ? AND exchange = ? AND interval = ? 
                AND datetime BETWEEN ? AND ? 
                ORDER BY datetime
                """,
                (symbol, exchange.value, interval.value, start, end)
            )
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Convert to BarData objects
            for row in rows:
                bar = BarData(
                    symbol=row[0],
                    exchange=Exchange(row[1]),
                    datetime=datetime.fromisoformat(row[2].isoformat()),
                    interval=Interval(row[3]),
                    volume=row[4],
                    turnover=row[5],
                    open_interest=row[6],
                    open_price=row[7],
                    high_price=row[8],
                    low_price=row[9],
                    close_price=row[10],
                    gateway_name="DB"
                )
                bars.append(bar)
                
        except Exception as e:
            print(f"Load bar data failed: {e}")
        
        return bars
    
    def load_tick_data(
        self, 
        symbol: str, 
        exchange: Exchange, 
        start: datetime, 
        end: datetime
    ) -> List[TickData]:
        ticks: List[TickData] = []
        
        try:
            cursor = self.conn.cursor()
            
            # Convert datetime timezone
            start = convert_tz(start)
            end = convert_tz(end)
            
            # Query tick data
            cursor.execute(
                """
                SELECT * FROM tick_data 
                WHERE symbol = ? AND exchange = ? 
                AND datetime BETWEEN ? AND ? 
                ORDER BY datetime
                """,
                (symbol, exchange.value, start, end)
            )
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Convert to TickData objects
            for row in rows:
                tick = TickData(
                    symbol=row[0],
                    exchange=Exchange(row[1]),
                    datetime=datetime.fromisoformat(row[2].isoformat()),
                    name=row[3],
                    volume=row[4],
                    turnover=row[5],
                    open_interest=row[6],
                    last_price=row[7],
                    last_volume=row[8],
                    limit_up=row[9],
                    limit_down=row[10],
                    open_price=row[11],
                    high_price=row[12],
                    low_price=row[13],
                    pre_close=row[14],
                    bid_price_1=row[15],
                    bid_volume_1=row[16],
                    ask_price_1=row[17],
                    ask_volume_1=row[18],
                    bid_price_2=row[19],
                    bid_volume_2=row[20],
                    ask_price_2=row[21],
                    ask_volume_2=row[22],
                    bid_price_3=row[23],
                    bid_volume_3=row[24],
                    ask_price_3=row[25],
                    ask_volume_3=row[26],
                    bid_price_4=row[27],
                    bid_volume_4=row[28],
                    ask_price_4=row[29],
                    ask_volume_4=row[30],
                    bid_price_5=row[31],
                    bid_volume_5=row[32],
                    ask_price_5=row[33],
                    ask_volume_5=row[34],
                    gateway_name="DB"
                )
                ticks.append(tick)
                
        except Exception as e:
            print(f"Load tick data failed: {e}")
        
        return ticks
    
    def delete_bar_data(
        self, 
        symbol: str, 
        exchange: Exchange, 
        interval: Interval
    ) -> int:
        try:
            cursor = self.conn.cursor()
            
            # Delete bar data
            cursor.execute(
                """
                DELETE FROM bar_data 
                WHERE symbol = ? AND exchange = ? AND interval = ?
                """,
                (symbol, exchange.value, interval.value)
            )
            
            count = cursor.rowcount
            self.conn.commit()
            return count
        except Exception as e:
            print(f"Delete bar data failed: {e}")
            return 0
    
    def delete_tick_data(
        self, 
        symbol: str, 
        exchange: Exchange
    ) -> int:
        try:
            cursor = self.conn.cursor()
            
            # Delete tick data
            cursor.execute(
                """
                DELETE FROM tick_data 
                WHERE symbol = ? AND exchange = ?
                """,
                (symbol, exchange.value)
            )
            
            count = cursor.rowcount
            self.conn.commit()
            return count
        except Exception as e:
            print(f"Delete tick data failed: {e}")
            return 0
    
    def get_bar_overview(self) -> List[BarOverview]:
        overviews: List[BarOverview] = []
        
        try:
            cursor = self.conn.cursor()
            
            # Query bar overview
            cursor.execute("""
                SELECT symbol, exchange, interval, 
                       COUNT(*) as count, 
                       MIN(datetime) as start, 
                       MAX(datetime) as end
                FROM bar_data 
                GROUP BY symbol, exchange, interval
            """)
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Convert to BarOverview objects
            for row in rows:
                overview = BarOverview(
                    symbol=row[0],
                    exchange=Exchange(row[1]),
                    interval=Interval(row[2]),
                    count=row[3],
                    start=row[4],
                    end=row[5]
                )
                overviews.append(overview)
                
        except Exception as e:
            print(f"Get bar overview failed: {e}")
        
        return overviews
    
    def get_tick_overview(self) -> List[TickOverview]:
        overviews: List[TickOverview] = []
        
        try:
            cursor = self.conn.cursor()
            
            # Query tick overview
            cursor.execute("""
                SELECT symbol, exchange, 
                       COUNT(*) as count, 
                       MIN(datetime) as start, 
                       MAX(datetime) as end
                FROM tick_data 
                GROUP BY symbol, exchange
            """)
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Convert to TickOverview objects
            for row in rows:
                overview = TickOverview(
                    symbol=row[0],
                    exchange=Exchange(row[1]),
                    count=row[2],
                    start=row[3],
                    end=row[4]
                )
                overviews.append(overview)
                
        except Exception as e:
            print(f"Get tick overview failed: {e}")
        
        return overviews