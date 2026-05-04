import sqlite3
import os
from datetime import datetime
import json


class SimpleSqliteDatabase:
    """
    A simple SQLite database implementation for storing and retrieving market data.
    Compatible with Python 3.9+
    """
    
    def __init__(self, db_path="market_data.db"):
        """
        Initialize the database.
        """
        self.db_path = db_path
        self.conn = None
        self.init_db()
    
    def init_db(self):
        """
        Create the database and tables if they don't exist.
        """
        # Create directory if not exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # Connect to database
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        
        cursor = self.conn.cursor()
        
        # Create bar data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bar_data (
                symbol TEXT,
                exchange TEXT,
                datetime TIMESTAMP,
                interval TEXT,
                volume INTEGER,
                turnover REAL,
                open_interest INTEGER,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
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
                turnover REAL,
                open_interest INTEGER,
                last_price REAL,
                last_volume INTEGER,
                limit_up REAL,
                limit_down REAL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                pre_close REAL,
                bid_price_1 REAL,
                bid_volume_1 INTEGER,
                ask_price_1 REAL,
                ask_volume_1 INTEGER,
                bid_price_2 REAL,
                bid_volume_2 INTEGER,
                ask_price_2 REAL,
                ask_volume_2 INTEGER,
                bid_price_3 REAL,
                bid_volume_3 INTEGER,
                ask_price_3 REAL,
                ask_volume_3 INTEGER,
                bid_price_4 REAL,
                bid_volume_4 INTEGER,
                ask_price_4 REAL,
                ask_volume_4 INTEGER,
                bid_price_5 REAL,
                bid_volume_5 INTEGER,
                ask_price_5 REAL,
                ask_volume_5 INTEGER,
                PRIMARY KEY (symbol, exchange, datetime)
            )
        """)
        
        # Create indices for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bar_symbol_exchange_interval ON bar_data (symbol, exchange, interval)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bar_datetime ON bar_data (datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tick_symbol_exchange ON tick_data (symbol, exchange)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tick_datetime ON tick_data (datetime)")
        
        self.conn.commit()
    
    def save_bar_data(self, bars):
        """
        Save bar data to database.
        Bars should be a list of dictionaries with the required fields.
        """
        if not bars:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            for bar in bars:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO bar_data 
                    (symbol, exchange, datetime, interval, volume, turnover, open_interest, 
                     open_price, high_price, low_price, close_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (bar['symbol'], bar['exchange'], bar['datetime'], bar['interval'],
                     bar['volume'], bar['turnover'], bar['open_interest'],
                     bar['open_price'], bar['high_price'], bar['low_price'], bar['close_price'])
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving bar data: {e}")
            return False
    
    def save_tick_data(self, ticks):
        """
        Save tick data to database.
        Ticks should be a list of dictionaries with the required fields.
        """
        if not ticks:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            for tick in ticks:
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
                    (tick['symbol'], tick['exchange'], tick['datetime'], tick['name'],
                     tick['volume'], tick['turnover'], tick['open_interest'], tick['last_price'],
                     tick['last_volume'], tick['limit_up'], tick['limit_down'], tick['open_price'],
                     tick['high_price'], tick['low_price'], tick['pre_close'], tick['bid_price_1'],
                     tick['bid_volume_1'], tick['ask_price_1'], tick['ask_volume_1'], tick['bid_price_2'],
                     tick['bid_volume_2'], tick['ask_price_2'], tick['ask_volume_2'], tick['bid_price_3'],
                     tick['bid_volume_3'], tick['ask_price_3'], tick['ask_volume_3'], tick['bid_price_4'],
                     tick['bid_volume_4'], tick['ask_price_4'], tick['ask_volume_4'], tick['bid_price_5'],
                     tick['bid_volume_5'], tick['ask_price_5'], tick['ask_volume_5'])
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving tick data: {e}")
            return False
    
    def load_bar_data(self, symbol, exchange, interval, start, end):
        """
        Load bar data from database.
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM bar_data 
                WHERE symbol = ? AND exchange = ? AND interval = ? 
                AND datetime BETWEEN ? AND ? 
                ORDER BY datetime
                """,
                (symbol, exchange, interval, start, end)
            )
            
            rows = cursor.fetchall()
            bars = []
            for row in rows:
                bars.append({
                    'symbol': row[0],
                    'exchange': row[1],
                    'datetime': row[2],
                    'interval': row[3],
                    'volume': row[4],
                    'turnover': row[5],
                    'open_interest': row[6],
                    'open_price': row[7],
                    'high_price': row[8],
                    'low_price': row[9],
                    'close_price': row[10]
                })
            
            return bars
        except Exception as e:
            print(f"Error loading bar data: {e}")
            return []
    
    def load_tick_data(self, symbol, exchange, start, end):
        """
        Load tick data from database.
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM tick_data 
                WHERE symbol = ? AND exchange = ? 
                AND datetime BETWEEN ? AND ? 
                ORDER BY datetime
                """,
                (symbol, exchange, start, end)
            )
            
            rows = cursor.fetchall()
            ticks = []
            for row in rows:
                ticks.append({
                    'symbol': row[0],
                    'exchange': row[1],
                    'datetime': row[2],
                    'name': row[3],
                    'volume': row[4],
                    'turnover': row[5],
                    'open_interest': row[6],
                    'last_price': row[7],
                    'last_volume': row[8],
                    'limit_up': row[9],
                    'limit_down': row[10],
                    'open_price': row[11],
                    'high_price': row[12],
                    'low_price': row[13],
                    'pre_close': row[14],
                    'bid_price_1': row[15],
                    'bid_volume_1': row[16],
                    'ask_price_1': row[17],
                    'ask_volume_1': row[18],
                    'bid_price_2': row[19],
                    'bid_volume_2': row[20],
                    'ask_price_2': row[21],
                    'ask_volume_2': row[22],
                    'bid_price_3': row[23],
                    'bid_volume_3': row[24],
                    'ask_price_3': row[25],
                    'ask_volume_3': row[26],
                    'bid_price_4': row[27],
                    'bid_volume_4': row[28],
                    'ask_price_4': row[29],
                    'ask_volume_4': row[30],
                    'bid_price_5': row[31],
                    'bid_volume_5': row[32],
                    'ask_price_5': row[33],
                    'ask_volume_5': row[34]
                })
            
            return ticks
        except Exception as e:
            print(f"Error loading tick data: {e}")
            return []
    
    def delete_bar_data(self, symbol, exchange, interval):
        """
        Delete bar data from database.
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "DELETE FROM bar_data WHERE symbol = ? AND exchange = ? AND interval = ?",
                (symbol, exchange, interval)
            )
            
            count = cursor.rowcount
            self.conn.commit()
            return count
        except Exception as e:
            print(f"Error deleting bar data: {e}")
            return 0
    
    def delete_tick_data(self, symbol, exchange):
        """
        Delete tick data from database.
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "DELETE FROM tick_data WHERE symbol = ? AND exchange = ?",
                (symbol, exchange)
            )
            
            count = cursor.rowcount
            self.conn.commit()
            return count
        except Exception as e:
            print(f"Error deleting tick data: {e}")
            return 0
    
    def get_bar_overview(self):
        """
        Get overview of bar data in database.
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT symbol, exchange, interval, 
                       COUNT(*) as count, 
                       MIN(datetime) as start, 
                       MAX(datetime) as end
                FROM bar_data 
                GROUP BY symbol, exchange, interval
            """)
            
            rows = cursor.fetchall()
            overview = []
            for row in rows:
                overview.append({
                    'symbol': row[0],
                    'exchange': row[1],
                    'interval': row[2],
                    'count': row[3],
                    'start': row[4],
                    'end': row[5]
                })
            
            return overview
        except Exception as e:
            print(f"Error getting bar overview: {e}")
            return []
    
    def get_tick_overview(self):
        """
        Get overview of tick data in database.
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT symbol, exchange, 
                       COUNT(*) as count, 
                       MIN(datetime) as start, 
                       MAX(datetime) as end
                FROM tick_data 
                GROUP BY symbol, exchange
            """)
            
            rows = cursor.fetchall()
            overview = []
            for row in rows:
                overview.append({
                    'symbol': row[0],
                    'exchange': row[1],
                    'count': row[2],
                    'start': row[3],
                    'end': row[4]
                })
            
            return overview
        except Exception as e:
            print(f"Error getting tick overview: {e}")
            return []
    
    def close(self):
        """
        Close the database connection.
        """
        if self.conn:
            self.conn.close()
            self.conn = None


# Test the database implementation
def test_database():
    """
    Test the simple SQLite database implementation.
    """
    print("Testing SimpleSqliteDatabase...")
    
    # Create database instance
    db = SimpleSqliteDatabase("test_market_data.db")
    
    # Test save bar data
    bars = []
    for i in range(10):
        dt = datetime(2023, 1, 1) + timedelta(days=i)
        bar = {
            'symbol': '000001',
            'exchange': 'SZSE',
            'datetime': dt,
            'interval': '1d',
            'volume': i * 1000,
            'turnover': i * 100000,
            'open_interest': 0,
            'open_price': 10 + i * 0.1,
            'high_price': 10 + i * 0.1 + 0.5,
            'low_price': 10 + i * 0.1 - 0.2,
            'close_price': 10 + i * 0.1 + 0.1
        }
        bars.append(bar)
    
    print(f"Saving {len(bars)} bars...")
    result = db.save_bar_data(bars)
    print(f"Save result: {result}")
    
    # Test load bar data
    print("Loading bars...")
    loaded_bars = db.load_bar_data(
        symbol='000001',
        exchange='SZSE',
        interval='1d',
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 10)
    )
    print(f"Loaded {len(loaded_bars)} bars")
    
    if loaded_bars:
        print("First loaded bar:")
        print(f"  Symbol: {loaded_bars[0]['symbol']}")
        print(f"  DateTime: {loaded_bars[0]['datetime']}")
        print(f"  Open: {loaded_bars[0]['open_price']}")
        print(f"  High: {loaded_bars[0]['high_price']}")
        print(f"  Low: {loaded_bars[0]['low_price']}")
        print(f"  Close: {loaded_bars[0]['close_price']}")
    
    # Test get bar overview
    print("Getting bar overview...")
    overview = db.get_bar_overview()
    print(f"Bar overview count: {len(overview)}")
    for item in overview:
        print(f"  {item['symbol']}.{item['exchange']} - {item['interval']}: {item['count']} bars")
    
    # Test delete bar data
    print("Deleting bars...")
    delete_count = db.delete_bar_data('000001', 'SZSE', '1d')
    print(f"Deleted {delete_count} bars")
    
    # Clean up
    db.close()
    if os.path.exists("test_market_data.db"):
        os.remove("test_market_data.db")
    
    print("Database test completed successfully!")


if __name__ == "__main__":
    from datetime import timedelta
    test_database()