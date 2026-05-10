from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging

import polars as pl

from .constant import Exchange, Interval
from .object import HistoryRequest
from .database import get_database, BarOverview
from .utility import extract_vt_symbol

logger = logging.getLogger(__name__)


class DataStatus(Enum):
    """数据状态枚举"""
    MISSING = "missing"           # 数据缺失（可能未上市）
    PARTIAL = "partial"           # 部分数据
    COMPLETE = "complete"         # 完整数据
    FETCH_FAILED = "fetch_failed" # 获取失败（可能跨越上市/退市时间点）


@dataclass
class StockMetadata:
    """
    股票元信息，包含上市/退市时间和缓存状态
    
    支持 AlphaLab 的 Parquet 文件缓存结构，按 interval 区分缓存
    """
    symbol: str = ""
    exchange: Exchange = None
    listed_date: Optional[datetime] = None  # 上市日期
    delisted_date: Optional[datetime] = None  # 退市日期（None表示仍在上市）
    first_trade_date: Optional[datetime] = None  # 实际第一笔交易日期
    last_trade_date: Optional[datetime] = None  # 实际最后一笔交易日期
    
    # Parquet 缓存 - 日线
    parquet_daily_start: Optional[datetime] = None
    parquet_daily_end: Optional[datetime] = None
    parquet_daily_count: Optional[int] = None  # 记录条数
    
    # Parquet 缓存 - 分钟线
    parquet_minute_start: Optional[datetime] = None
    parquet_minute_end: Optional[datetime] = None
    parquet_minute_count: Optional[int] = None  # 记录条数
    
    # 数据库缓存
    db_start: Optional[datetime] = None  # 数据库缓存起始时间
    db_end: Optional[datetime] = None  # 数据库缓存结束时间
    
    # 本地文件路径（AlphaLab 缓存位置）
    lab_path: Optional[str] = None  # AlphaLab 根目录路径
    
    data_status: DataStatus = DataStatus.MISSING
    last_fetch_time: Optional[datetime] = None  # 最后获取时间
    fetch_attempts: int = 0  # 获取尝试次数
    
    @property
    def vt_symbol(self) -> str:
        """获取 vt_symbol（用于 AlphaLab 文件名）"""
        if self.symbol and self.exchange:
            return f"{self.symbol}.{self.exchange.value}"
        return ""


class StockMetadataManager:
    """
    股票元信息管理器
    负责：
    1. 管理股票上市/退市时间
    2. 记录缓存状态（同时支持 AlphaLab Parquet 和数据库缓存）
    3. 提供一致性检查
    4. 避免重复获取不存在的数据
    5. 扫描和同步 AlphaLab 缓存目录
    """
    
    def __init__(self):
        self.database = get_database()
        self._init_tables()
        self._cache: Dict[str, StockMetadata] = {}  # 内存缓存
    
    def _init_tables(self):
        """初始化股票元信息表（支持 AlphaLab Parquet 缓存结构）"""
        conn = self.database.conn
        cursor = conn.cursor()
        
        # 先检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='stock_metadata'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # 创建新表
            cursor.execute("""
                CREATE TABLE stock_metadata (
                    symbol TEXT,
                    exchange TEXT,
                    listed_date TIMESTAMP,
                    delisted_date TIMESTAMP,
                    first_trade_date TIMESTAMP,
                    last_trade_date TIMESTAMP,
                    parquet_daily_start TIMESTAMP,
                    parquet_daily_end TIMESTAMP,
                    parquet_daily_count INTEGER,
                    parquet_minute_start TIMESTAMP,
                    parquet_minute_end TIMESTAMP,
                    parquet_minute_count INTEGER,
                    db_start TIMESTAMP,
                    db_end TIMESTAMP,
                    lab_path TEXT,
                    data_status TEXT,
                    last_fetch_time TIMESTAMP,
                    fetch_attempts INTEGER,
                    PRIMARY KEY (symbol, exchange)
                )
            """)
        else:
            # 表已存在，需要添加缺失的列
            # 先获取现有列名
            cursor.execute("PRAGMA table_info(stock_metadata)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            # 需要添加的新列
            new_columns = [
                ("parquet_daily_start", "TIMESTAMP"),
                ("parquet_daily_end", "TIMESTAMP"),
                ("parquet_daily_count", "INTEGER"),
                ("parquet_minute_start", "TIMESTAMP"),
                ("parquet_minute_end", "TIMESTAMP"),
                ("parquet_minute_count", "INTEGER"),
                ("lab_path", "TEXT")
            ]
            
            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE stock_metadata ADD COLUMN {col_name} {col_type}")
                        logger.info(f"Added column {col_name} to stock_metadata table")
                    except Exception as e:
                        logger.warning(f"Failed to add column {col_name}: {e}")
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_metadata_symbol_exchange 
            ON stock_metadata (symbol, exchange)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_metadata_listed_date 
            ON stock_metadata (listed_date)
        """)
        
        conn.commit()
    
    def _get_key(self, symbol: str, exchange: Exchange) -> str:
        """生成股票唯一标识key"""
        return f"{symbol}_{exchange.value}"
    
    def get_metadata(self, symbol: str, exchange: Exchange) -> Optional[StockMetadata]:
        """获取股票元信息"""
        key = self._get_key(symbol, exchange)
        
        # 先检查内存缓存
        if key in self._cache:
            return self._cache[key]
        
        # 从数据库读取
        try:
            conn = self.database.conn
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM stock_metadata 
                WHERE symbol = ? AND exchange = ?
            """, (symbol, exchange.value))
            
            row = cursor.fetchone()
            
            if row:
                # 处理可能为None的data_status
                data_status_value = row[15]
                try:
                    data_status_enum = DataStatus(data_status_value) if data_status_value else DataStatus.MISSING
                except (ValueError, TypeError):
                    data_status_enum = DataStatus.MISSING
                
                # 安全地转换日期字段
                def _safe_datetime(value):
                    if value is None:
                        return None
                    # 处理无效的字符串值（如 '0'）
                    if isinstance(value, str) and (value == '0' or value == '' or len(value) < 10):
                        return None
                    return value
                
                metadata = StockMetadata(
                    symbol=row[0],
                    exchange=Exchange(row[1]),
                    listed_date=_safe_datetime(row[2]),
                    delisted_date=_safe_datetime(row[3]),
                    first_trade_date=_safe_datetime(row[4]),
                    last_trade_date=_safe_datetime(row[5]),
                    parquet_daily_start=_safe_datetime(row[6]),
                    parquet_daily_end=_safe_datetime(row[7]),
                    parquet_daily_count=row[8],
                    parquet_minute_start=_safe_datetime(row[9]),
                    parquet_minute_end=_safe_datetime(row[10]),
                    parquet_minute_count=row[11],
                    db_start=_safe_datetime(row[12]),
                    db_end=_safe_datetime(row[13]),
                    lab_path=row[14],
                    data_status=data_status_enum,
                    last_fetch_time=_safe_datetime(row[16]),
                    fetch_attempts=row[17]
                )
                self._cache[key] = metadata
                return metadata
            
        except Exception as e:
            logger.error(f"获取股票元信息失败 {symbol}.{exchange}: {e}")
        
        return None
    
    def save_metadata(self, metadata: StockMetadata) -> bool:
        """保存股票元信息"""
        try:
            conn = self.database.conn
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO stock_metadata (
                    symbol, exchange, listed_date, delisted_date,
                    first_trade_date, last_trade_date,
                    parquet_daily_start, parquet_daily_end, parquet_daily_count,
                    parquet_minute_start, parquet_minute_end, parquet_minute_count,
                    db_start, db_end,
                    lab_path,
                    data_status, last_fetch_time, fetch_attempts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.symbol,
                metadata.exchange.value,
                metadata.listed_date,
                metadata.delisted_date,
                metadata.first_trade_date,
                metadata.last_trade_date,
                metadata.parquet_daily_start,
                metadata.parquet_daily_end,
                metadata.parquet_daily_count,
                metadata.parquet_minute_start,
                metadata.parquet_minute_end,
                metadata.parquet_minute_count,
                metadata.db_start,
                metadata.db_end,
                metadata.lab_path,
                metadata.data_status.value,
                metadata.last_fetch_time,
                metadata.fetch_attempts
            ))
            
            conn.commit()
            
            # 更新内存缓存
            key = self._get_key(metadata.symbol, metadata.exchange)
            self._cache[key] = metadata
            
            return True
        except Exception as e:
            logger.error(f"保存股票元信息失败 {metadata.symbol}.{metadata.exchange}: {e}")
            return False
    
    def update_metadata_from_fetch(self, symbol: str, exchange: Exchange, 
                                   req: HistoryRequest, fetched_bars: List[Any], 
                                   fetch_success: bool):
        """
        根据获取结果更新元信息
        """
        metadata = self.get_metadata(symbol, exchange)
        if not metadata:
            metadata = StockMetadata(symbol=symbol, exchange=exchange)
        
        metadata.last_fetch_time = datetime.now()
        # 处理 fetch_attempts 可能为 None 的情况
        if metadata.fetch_attempts is None:
            metadata.fetch_attempts = 0
        metadata.fetch_attempts += 1
        
        if fetch_success and fetched_bars:
            # 更新实际交易日期范围
            first_bar = fetched_bars[0]
            last_bar = fetched_bars[-1]
            
            first_datetime = first_bar.datetime if hasattr(first_bar, 'datetime') else fetched_bars[0][0]
            last_datetime = last_bar.datetime if hasattr(last_bar, 'datetime') else fetched_bars[-1][0]
            
            if not metadata.first_trade_date or first_datetime < metadata.first_trade_date:
                metadata.first_trade_date = first_datetime
            if not metadata.last_trade_date or last_datetime > metadata.last_trade_date:
                metadata.last_trade_date = last_datetime
            
            # 更新数据状态
            if metadata.listed_date and metadata.delisted_date:
                # 已知道上市退市时间
                if (req.start >= metadata.listed_date and 
                    req.end <= metadata.delisted_date and
                    first_datetime <= req.start and 
                    last_datetime >= req.end):
                    metadata.data_status = DataStatus.COMPLETE
                else:
                    metadata.data_status = DataStatus.PARTIAL
            else:
                # 未知上市退市时间，根据获取结果判断
                if len(fetched_bars) > 0:
                    metadata.data_status = DataStatus.PARTIAL
                    
                    # 如果请求的起始时间之前没有数据，可能是还未上市
                    if first_datetime > req.start:
                        # 记录上市日期为第一个实际交易日期
                        metadata.listed_date = first_datetime
                
        elif not fetch_success or (fetch_success and not fetched_bars):
            # 获取失败或无数据，可能跨越上市/退市时间点
            metadata.data_status = DataStatus.FETCH_FAILED
            
            # 如果之前有数据，现在获取失败，可能已经退市
            if metadata.last_trade_date and req.start > metadata.last_trade_date:
                if not metadata.delisted_date:
                    metadata.delisted_date = metadata.last_trade_date
        
        self.save_metadata(metadata)
    
    def check_date_range(self, symbol: str, exchange: Exchange, 
                         start: datetime, end: datetime) -> Dict[str, Any]:
        """
        检查请求的日期范围是否有效（考虑上市/退市时间）
        
        Returns:
            dict: 包含检查结果的字典
                - valid: bool - 是否有效
                - before_listed: bool - 是否在上市前
                - after_delisted: bool - 是否在退市后
                - actual_start: datetime - 实际有效的起始时间
                - actual_end: datetime - 实际有效的结束时间
                - metadata: StockMetadata - 股票元信息
                - message: str - 说明信息
        """
        metadata = self.get_metadata(symbol, exchange)
        
        result = {
            "valid": True,
            "before_listed": False,
            "after_delisted": False,
            "actual_start": start,
            "actual_end": end,
            "metadata": metadata,
            "message": ""
        }
        
        if not metadata:
            # 没有元信息，返回默认结果
            return result
        
        actual_start = start
        actual_end = end
        messages = []
        
        # 检查是否在上市前
        if metadata.listed_date and start < metadata.listed_date:
            result["before_listed"] = True
            actual_start = metadata.listed_date
            messages.append(f"请求起始时间早于上市日期 {metadata.listed_date}")
        
        # 检查是否在退市后
        if metadata.delisted_date and end > metadata.delisted_date:
            result["after_delisted"] = True
            actual_end = metadata.delisted_date
            messages.append(f"请求结束时间晚于退市日期 {metadata.delisted_date}")
        
        # 检查是否完全超出有效范围
        # 情况1：请求完全在上市前（只要有上市日期）
        if metadata.listed_date and end < metadata.listed_date:
            result["valid"] = False
            messages.append("请求时间范围完全在上市前")
        # 情况2：请求完全在退市后（只要有退市日期）
        elif metadata.delisted_date and start > metadata.delisted_date:
            result["valid"] = False
            messages.append("请求时间范围完全在退市后")
        
        result["actual_start"] = actual_start
        result["actual_end"] = actual_end
        result["message"] = "; ".join(messages)
        
        return result
    
    def validate_cache_consistency(self, symbol: str, exchange: Exchange, 
                                   interval: Interval) -> Dict[str, Any]:
        """
        验证数据库和parquet缓存的一致性
        
        Returns:
            dict: 包含检查结果的字典
                - consistent: bool - 是否一致
                - issues: List[str] - 问题列表
                - db_overview: BarOverview - 数据库概览
                - parquet_overview: dict - parquet概览
        """
        metadata = self.get_metadata(symbol, exchange)
        
        result = {
            "consistent": True,
            "issues": [],
            "db_overview": None,
            "parquet_overview": None
        }
        
        if not metadata:
            result["issues"].append("未找到股票元信息")
            result["consistent"] = False
            return result
        
        # 获取数据库概览
        db_overview = None
        try:
            overviews = self.database.get_bar_overview()
            for ov in overviews:
                if ov.symbol == symbol and ov.exchange == exchange and ov.interval == interval:
                    db_overview = ov
                    break
        except Exception as e:
            result["issues"].append(f"获取数据库概览失败: {e}")
        
        result["db_overview"] = db_overview
        
        # 获取parquet概览（从元信息中读取，支持 AlphaLab 结构）
        parquet_overview = {
            "daily_start": metadata.parquet_daily_start,
            "daily_end": metadata.parquet_daily_end,
            "daily_count": metadata.parquet_daily_count,
            "minute_start": metadata.parquet_minute_start,
            "minute_end": metadata.parquet_minute_end,
            "minute_count": metadata.parquet_minute_count
        }
        result["parquet_overview"] = parquet_overview
        
        # 检查一致性
        if db_overview:
            # 比较数据库和元信息中的db时间范围
            if metadata.db_start and db_overview.start and metadata.db_start != db_overview.start:
                result["issues"].append(
                    f"元信息中db_start与实际数据库不一致: "
                    f"元信息={metadata.db_start}, 实际={db_overview.start}"
                )
            if metadata.db_end and db_overview.end and metadata.db_end != db_overview.end:
                result["issues"].append(
                    f"元信息中db_end与实际数据库不一致: "
                    f"元信息={metadata.db_end}, 实际={db_overview.end}"
                )
            
            # 比较数据库和parquet的时间范围（按周期分别比较）
            # 注意：db_overview.start/end 可能是字符串类型（SQLite返回）
            try:
                db_start = db_overview.start
                db_end = db_overview.end
                
                # 如果是字符串类型，转换为datetime
                if isinstance(db_start, str):
                    db_start = datetime.fromisoformat(db_start)
                if isinstance(db_end, str):
                    db_end = datetime.fromisoformat(db_end)
                
                # 日线比较
                if (db_start and metadata.parquet_daily_start and 
                    abs((db_start - metadata.parquet_daily_start).days) > 1):
                    result["issues"].append(
                        f"数据库与日线parquet起始时间不一致: "
                        f"数据库={db_overview.start}, parquet={metadata.parquet_daily_start}"
                    )
                if (db_end and metadata.parquet_daily_end and 
                    abs((db_end - metadata.parquet_daily_end).days) > 1):
                    result["issues"].append(
                        f"数据库与日线parquet结束时间不一致: "
                        f"数据库={db_overview.end}, parquet={metadata.parquet_daily_end}"
                    )
            except Exception as e:
                result["issues"].append(f"比较时间范围时出错: {e}")
        else:
            if metadata.db_start or metadata.db_end:
                result["issues"].append(
                    "元信息中记录了数据库缓存，但实际数据库中不存在该股票数据"
                )
        
        # 检查parquet记录是否与实际AlphaLab文件一致
        if metadata.parquet_daily_start or metadata.parquet_minute_start:
            if metadata.lab_path:
                lab_path = Path(metadata.lab_path)
                vt_symbol = metadata.vt_symbol
                
                # 检查日线文件
                if metadata.parquet_daily_start:
                    daily_file = lab_path / "daily" / f"{vt_symbol}.parquet"
                    if not daily_file.exists():
                        result["issues"].append(
                            f"元信息中记录了日线parquet缓存，但文件不存在: {daily_file}"
                        )
                
                # 检查分钟线文件
                if metadata.parquet_minute_start:
                    minute_file = lab_path / "minute" / f"{vt_symbol}.parquet"
                    if not minute_file.exists():
                        result["issues"].append(
                            f"元信息中记录了分钟线parquet缓存，但文件不存在: {minute_file}"
                        )
        
        result["consistent"] = len(result["issues"]) == 0
        
        return result
    
    def update_parquet_metadata(self, symbol: str, exchange: Exchange, 
                                interval: Interval, start: datetime, end: datetime, 
                                count: Optional[int] = None):
        """
        更新parquet缓存元信息（支持 AlphaLab 结构）
        
        Args:
            symbol: 股票代码
            exchange: 交易所
            interval: 时间周期（DAILY/MINUTE）
            start: 起始时间
            end: 结束时间
            count: 记录条数（可选）
        """
        metadata = self.get_metadata(symbol, exchange)
        if not metadata:
            metadata = StockMetadata(symbol=symbol, exchange=exchange)
        
        # 根据周期更新不同的缓存字段
        if interval == Interval.DAILY:
            if not metadata.parquet_daily_start or start < metadata.parquet_daily_start:
                metadata.parquet_daily_start = start
            if not metadata.parquet_daily_end or end > metadata.parquet_daily_end:
                metadata.parquet_daily_end = end
            if count is not None:
                metadata.parquet_daily_count = count
        elif interval == Interval.MINUTE:
            if not metadata.parquet_minute_start or start < metadata.parquet_minute_start:
                metadata.parquet_minute_start = start
            if not metadata.parquet_minute_end or end > metadata.parquet_minute_end:
                metadata.parquet_minute_end = end
            if count is not None:
                metadata.parquet_minute_count = count
        
        self.save_metadata(metadata)
    
    def scan_alpha_lab_cache(self, lab_path: str) -> Dict[str, Any]:
        """
        扫描 AlphaLab 缓存目录，更新元信息
        
        Args:
            lab_path: AlphaLab 根目录路径
            
        Returns:
            dict: 扫描结果统计
        """
        lab_path = Path(lab_path)
        daily_path = lab_path / "daily"
        minute_path = lab_path / "minute"
        
        result = {
            "scanned_daily": 0,
            "scanned_minute": 0,
            "updated": 0,
            "new_stocks": 0,
            "errors": []
        }
        
        # 扫描日线缓存
        if daily_path.exists():
            for parquet_file in daily_path.glob("*.parquet"):
                try:
                    vt_symbol = parquet_file.stem
                    symbol, exchange = extract_vt_symbol(vt_symbol)
                    
                    # 读取parquet文件获取时间范围
                    df = pl.read_parquet(parquet_file)
                    if "datetime" in df.columns:
                        # 获取最小和最大时间（兼容不同版本的Polars）
                        min_dt_raw = df["datetime"].min()
                        max_dt_raw = df["datetime"].max()
                        
                        # Polars 0.19+ 使用 .item() 或直接转换
                        if hasattr(min_dt_raw, 'to_python'):
                            min_dt = min_dt_raw.to_python()
                            max_dt = max_dt_raw.to_python()
                        elif hasattr(min_dt_raw, 'item'):
                            min_dt = min_dt_raw.item()
                            max_dt = max_dt_raw.item()
                        else:
                            min_dt = min_dt_raw
                            max_dt = max_dt_raw
                            
                        count = len(df)
                        
                        # 获取或创建元信息
                        metadata = self.get_metadata(symbol, exchange)
                        is_new = metadata is None
                        if is_new:
                            metadata = StockMetadata(symbol=symbol, exchange=exchange)
                        
                        # 更新缓存信息
                        metadata.parquet_daily_start = min_dt
                        metadata.parquet_daily_end = max_dt
                        metadata.parquet_daily_count = count
                        metadata.lab_path = str(lab_path)
                        
                        # 如果有数据，标记为PARTIAL（需要完整数据才标记COMPLETE）
                        if metadata.data_status == DataStatus.MISSING:
                            metadata.data_status = DataStatus.PARTIAL
                        
                        self.save_metadata(metadata)
                        
                        result["scanned_daily"] += 1
                        result["updated"] += 1
                        if is_new:
                            result["new_stocks"] += 1
                except Exception as e:
                    result["errors"].append(f"扫描日线 {parquet_file.name} 失败: {e}")
        
        # 扫描分钟线缓存
        if minute_path.exists():
            for parquet_file in minute_path.glob("*.parquet"):
                try:
                    vt_symbol = parquet_file.stem
                    symbol, exchange = extract_vt_symbol(vt_symbol)
                    
                    # 读取parquet文件获取时间范围
                    df = pl.read_parquet(parquet_file)
                    if "datetime" in df.columns:
                        # 获取最小和最大时间（兼容不同版本的Polars）
                        min_dt_raw = df["datetime"].min()
                        max_dt_raw = df["datetime"].max()
                        
                        # Polars 0.19+ 使用 .item() 或直接转换
                        if hasattr(min_dt_raw, 'to_python'):
                            min_dt = min_dt_raw.to_python()
                            max_dt = max_dt_raw.to_python()
                        elif hasattr(min_dt_raw, 'item'):
                            min_dt = min_dt_raw.item()
                            max_dt = max_dt_raw.item()
                        else:
                            min_dt = min_dt_raw
                            max_dt = max_dt_raw
                            
                        count = len(df)
                        
                        # 获取或创建元信息
                        metadata = self.get_metadata(symbol, exchange)
                        is_new = metadata is None
                        if is_new:
                            metadata = StockMetadata(symbol=symbol, exchange=exchange)
                        
                        # 更新缓存信息
                        metadata.parquet_minute_start = min_dt
                        metadata.parquet_minute_end = max_dt
                        metadata.parquet_minute_count = count
                        metadata.lab_path = str(lab_path)
                        
                        # 如果有数据，标记为PARTIAL
                        if metadata.data_status == DataStatus.MISSING:
                            metadata.data_status = DataStatus.PARTIAL
                        
                        self.save_metadata(metadata)
                        
                        result["scanned_minute"] += 1
                        result["updated"] += 1
                        if is_new:
                            result["new_stocks"] += 1
                except Exception as e:
                    result["errors"].append(f"扫描分钟线 {parquet_file.name} 失败: {e}")
        
        logger.info(f"AlphaLab 缓存扫描完成: 日线 {result['scanned_daily']} 个, 分钟线 {result['scanned_minute']} 个, 更新 {result['updated']} 个, 新股票 {result['new_stocks']} 个")
        
        return result
    
    def update_db_metadata(self, symbol: str, exchange: Exchange, 
                           interval: Interval, start: datetime, end: datetime):
        """更新数据库缓存元信息"""
        metadata = self.get_metadata(symbol, exchange)
        if not metadata:
            metadata = StockMetadata(symbol=symbol, exchange=exchange)
        
        # 更新数据库缓存时间范围
        if not metadata.db_start or start < metadata.db_start:
            metadata.db_start = start
        if not metadata.db_end or end > metadata.db_end:
            metadata.db_end = end
        
        self.save_metadata(metadata)
    
    def mark_fetch_failed(self, symbol: str, exchange: Exchange, reason: str = ""):
        """标记数据获取失败"""
        metadata = self.get_metadata(symbol, exchange)
        if not metadata:
            metadata = StockMetadata(symbol=symbol, exchange=exchange)
        
        metadata.data_status = DataStatus.FETCH_FAILED
        metadata.last_fetch_time = datetime.now()
        # 处理 fetch_attempts 可能为 None 的情况
        if metadata.fetch_attempts is None:
            metadata.fetch_attempts = 0
        metadata.fetch_attempts += 1
        
        self.save_metadata(metadata)
    
    def update_listed_date(self, symbol: str, exchange: Exchange, listed_date: datetime):
        """更新股票上市日期"""
        metadata = self.get_metadata(symbol, exchange)
        if not metadata:
            metadata = StockMetadata(symbol=symbol, exchange=exchange)
        
        metadata.listed_date = listed_date
        self.save_metadata(metadata)
    
    def update_delisted_date(self, symbol: str, exchange: Exchange, delisted_date: datetime):
        """更新股票退市日期"""
        metadata = self.get_metadata(symbol, exchange)
        if not metadata:
            metadata = StockMetadata(symbol=symbol, exchange=exchange)
        
        metadata.delisted_date = delisted_date
        self.save_metadata(metadata)
    
    def get_stocks_with_status(self, status: DataStatus) -> List[StockMetadata]:
        """获取指定状态的所有股票"""
        try:
            conn = self.database.conn
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM stock_metadata 
                WHERE data_status = ?
            """, (status.value,))
            
            rows = cursor.fetchall()
            result = []
            
            for row in rows:
                # 处理可能为None的data_status
                data_status_value = row[15]
                try:
                    data_status_enum = DataStatus(data_status_value) if data_status_value else DataStatus.MISSING
                except (ValueError, TypeError):
                    data_status_enum = DataStatus.MISSING
                
                metadata = StockMetadata(
                    symbol=row[0],
                    exchange=Exchange(row[1]),
                    listed_date=row[2],
                    delisted_date=row[3],
                    first_trade_date=row[4],
                    last_trade_date=row[5],
                    parquet_daily_start=row[6],
                    parquet_daily_end=row[7],
                    parquet_daily_count=row[8],
                    parquet_minute_start=row[9],
                    parquet_minute_end=row[10],
                    parquet_minute_count=row[11],
                    db_start=row[12],
                    db_end=row[13],
                    lab_path=row[14],
                    data_status=data_status_enum,
                    last_fetch_time=row[16],
                    fetch_attempts=row[17]
                )
                result.append(metadata)
            
            return result
        except Exception as e:
            logger.error(f"获取状态为{status}的股票失败: {e}")
            return []
    
    def get_all_metadata(self) -> List[StockMetadata]:
        """获取所有股票元信息"""
        try:
            conn = self.database.conn
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM stock_metadata")
            
            rows = cursor.fetchall()
            result = []
            
            for row in rows:
                metadata = StockMetadata(
                    symbol=row[0],
                    exchange=Exchange(row[1]),
                    listed_date=row[2],
                    delisted_date=row[3],
                    first_trade_date=row[4],
                    last_trade_date=row[5],
                    parquet_daily_start=row[6],
                    parquet_daily_end=row[7],
                    parquet_daily_count=row[8],
                    parquet_minute_start=row[9],
                    parquet_minute_end=row[10],
                    parquet_minute_count=row[11],
                    db_start=row[12],
                    db_end=row[13],
                    lab_path=row[14],
                    data_status=DataStatus(row[15]),
                    last_fetch_time=row[16],
                    fetch_attempts=row[17]
                )
                result.append(metadata)
            
            return result
        except Exception as e:
            logger.error(f"获取所有股票元信息失败: {e}")
            return []
