#!/usr/bin/env python3
"""
EnhancedDataCache - 增强型数据缓存管理器

统一管理：
1. DataFeed 数据源（实时数据获取）
2. AlphaLab Parquet 缓存（历史数据存储）
3. StockMetadataManager（元信息管理）

提供统一的查询接口，自动处理：
- 上市/退市时间检查
- 缓存命中检测
- 数据下载与缓存
- 元信息同步
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import logging

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import HistoryRequest, BarData
from vnpy.trader.utility import extract_vt_symbol
from vnpy.trader.datafeed import get_datafeed, BaseDatafeed
from vnpy.trader.stock_metadata import StockMetadataManager, DataStatus
from vnpy.alpha.lab import AlphaLab

logger = logging.getLogger(__name__)


class QueryResult:
    """查询结果封装"""
    
    def __init__(self):
        self.bars: List[BarData] = []
        self.hit_cache: bool = False  # 是否命中缓存
        self.from_source: bool = False  # 是否从数据源获取
        self.skipped: bool = False  # 是否被跳过（上市前/退市后）
        self.skipped_reason: str = ""  # 跳过原因
        self.error: Optional[Exception] = None  # 错误信息
        self.metadata_updated: bool = False  # 元信息是否已更新


class EnhancedDataCache:
    """
    增强型数据缓存管理器
    
    统一管理 DataFeed、AlphaLab 和元信息，提供透明的数据查询接口
    """
    
    def __init__(self, lab_path: Optional[str] = None):
        """
        初始化缓存管理器
        
        :param lab_path: AlphaLab 数据目录路径，默认为 None（使用默认路径）
        """
        # 初始化 DataFeed
        self.datafeed: BaseDatafeed = get_datafeed()
        
        # 初始化 AlphaLab
        self.lab: AlphaLab = AlphaLab(lab_path) if lab_path else AlphaLab()
        
        # 初始化元信息管理器
        self.metadata_manager: StockMetadataManager = StockMetadataManager()
        
        # 缓存目录路径
        self.lab_path: str = self.lab.lab_path
        
        logger.info(f"EnhancedDataCache 初始化完成")
        logger.info(f"  - DataFeed: {self.datafeed.__class__.__name__}")
        logger.info(f"  - AlphaLab 路径: {self.lab_path}")
    
    def query_bar_history(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime,
        lookback_days: int = 0,
        force_refresh: bool = False
    ) -> QueryResult:
        """
        统一查询 K 线历史数据
        
        :param symbol: 股票代码
        :param exchange: 交易所
        :param interval: 时间周期
        :param start: 开始时间
        :param end: 结束时间
        :param lookback_days: 回溯窗口天数（用于指标计算）
        :param force_refresh: 是否强制刷新（跳过缓存）
        :return: QueryResult 查询结果
        """
        result = QueryResult()
        vt_symbol = f"{symbol}.{exchange.value}"
        
        try:
            # 1. 计算实际查询范围（包含回溯窗口）
            actual_start = start - timedelta(days=lookback_days) if lookback_days > 0 else start
            
            # 2. 检查上市/退市时间
            check_result = self.metadata_manager.check_date_range(
                symbol=symbol,
                exchange=exchange,
                start=actual_start,
                end=end
            )
            
            if not check_result["valid"]:
                result.skipped = True
                if check_result.get("before_listed"):
                    result.skipped_reason = f"查询范围在上市日期之前"
                elif check_result.get("after_delisted"):
                    result.skipped_reason = f"查询范围在退市日期之后"
                logger.info(f"⏭ {vt_symbol} 跳过: {result.skipped_reason}")
                return result
            
            # 3. 计算有效查询范围（考虑上市/退市时间）
            effective_start = actual_start
            effective_end = end
            
            metadata = self.metadata_manager.get_metadata(symbol, exchange)
            if check_result.get("partial_before_listed") and metadata and metadata.listed_date:
                effective_start = max(effective_start, metadata.listed_date)
            
            if check_result.get("partial_after_delisted") and metadata and metadata.delisted_date:
                effective_end = min(effective_end, metadata.delisted_date)
            
            # 4. 检查缓存（如果不强制刷新）
            if not force_refresh:
                cached_bars = self._load_from_cache(
                    vt_symbol, interval, effective_start, effective_end
                )
                
                if cached_bars:
                    result.bars = cached_bars
                    result.hit_cache = True
                    logger.debug(f"✓ {vt_symbol} 命中 AlphaLab 缓存 ({len(cached_bars)}条)")
                    return result
            
            # 5. 从数据源获取数据
            bars = self._fetch_from_source(
                symbol, exchange, interval, effective_start, effective_end
            )
            
            if bars:
                result.bars = bars
                result.from_source = True
                
                # 保存到 AlphaLab
                self.lab.save_bar_data(bars)
                logger.debug(f"✓ {vt_symbol} 从数据源获取并缓存 ({len(bars)}条)")
                
                # 更新元信息
                self._update_metadata(symbol, exchange, interval, bars)
                result.metadata_updated = True
            else:
                # 标记获取失败
                self.metadata_manager.mark_fetch_failed(symbol, exchange)
                logger.warning(f"✗ {vt_symbol} 未获取到数据")
        
        except Exception as e:
            result.error = e
            logger.error(f"✗ {vt_symbol} 查询失败: {e}", exc_info=True)
        
        return result
    
    def _load_from_cache(
        self,
        vt_symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """从 AlphaLab 缓存加载数据"""
        try:
            bars = self.lab.load_bar_data(vt_symbol, interval, start, end)
            
            if bars and len(bars) > 0:
                # 检查缓存是否完全覆盖请求范围
                bar_dates = [b.datetime for b in bars]
                cache_start = min(bar_dates)
                cache_end = max(bar_dates)
                
                # 情况1: 缓存完全覆盖请求范围 → 直接返回
                if cache_start <= start and cache_end >= end:
                    logger.debug(f"✓ {vt_symbol} 缓存完全命中")
                    return bars
                
                # 情况2: 缓存覆盖了请求的主要部分（回测核心区间）
                # 如果缓存覆盖了 start 到 end 的大部分，返回已有数据
                # 避免因为回溯窗口导致完全重新下载
                if cache_start <= end and cache_end >= start:
                    # 缓存与请求范围有重叠
                    logger.debug(f"⚠ {vt_symbol} 缓存部分命中，返回已有数据")
                    return bars
                
                # 情况3: 缓存完全不覆盖请求范围
                logger.debug(f"⚠ {vt_symbol} 缓存完全不覆盖请求范围")
        
        except Exception as e:
            logger.warning(f"✗ {vt_symbol} 加载缓存失败: {e}")
        
        return []
    
    def _fetch_from_source(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """从 DataFeed 数据源获取数据"""
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=start,
            end=end
        )
        
        try:
            return self.datafeed.query_bar_history(req)
        except Exception as e:
            logger.error(f"✗ {symbol}.{exchange.value} 从数据源获取失败: {e}")
            return []
    
    def _update_metadata(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        bars: List[BarData]
    ):
        """更新元信息"""
        if not bars:
            return
        
        bar_dates = [b.datetime for b in bars]
        data_start = min(bar_dates)
        data_end = max(bar_dates)
        
        # 更新 Parquet 缓存元信息
        self.metadata_manager.update_parquet_metadata(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=data_start,
            end=data_end,
            count=len(bars)
        )
        
        # 更新实际交易日期（首次获取时）
        metadata = self.metadata_manager.get_metadata(symbol, exchange)
        if not metadata or not metadata.first_trade_date:
            # 创建HistoryRequest对象
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=data_start,
                end=data_end
            )
            self.metadata_manager.update_metadata_from_fetch(symbol, exchange, req, bars, True)
        
        # 重置失败计数
        if metadata and metadata.fetch_attempts is not None and metadata.fetch_attempts > 0:
            metadata.fetch_attempts = 0
            self.metadata_manager.save_metadata(metadata)
    
    def batch_query(
        self,
        vt_symbols: List[str],
        interval: Interval,
        start: datetime,
        end: datetime,
        lookback_days: int = 0,
        force_refresh: bool = False
    ) -> Dict[str, QueryResult]:
        """
        批量查询多个标的
        
        :param vt_symbols: 标的列表（格式: "000001.SZSE"）
        :param interval: 时间周期
        :param start: 开始时间
        :param end: 结束时间
        :param lookback_days: 回溯窗口天数
        :param force_refresh: 是否强制刷新
        :return: 各标的查询结果字典
        """
        results: Dict[str, QueryResult] = {}
        
        for vt_symbol in vt_symbols:
            symbol, exchange = extract_vt_symbol(vt_symbol)
            result = self.query_bar_history(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=start,
                end=end,
                lookback_days=lookback_days,
                force_refresh=force_refresh
            )
            results[vt_symbol] = result
        
        return results
    
    def scan_lab_cache(self) -> Dict[str, Any]:
        """扫描 AlphaLab 缓存目录，更新元信息"""
        return self.metadata_manager.scan_alpha_lab_cache(self.lab_path)
    
    def validate_cache_consistency(self, vt_symbol: str, interval: Interval = Interval.DAILY) -> Dict[str, Any]:
        """验证指定标的的缓存一致性"""
        symbol, exchange = extract_vt_symbol(vt_symbol)
        return self.metadata_manager.validate_cache_consistency(symbol, exchange, interval)
    
    def get_metadata(self, symbol: str, exchange: Exchange) -> Optional[Any]:
        """获取股票元信息"""
        return self.metadata_manager.get_metadata(symbol, exchange)
    
    def get_stocks_with_status(self, status: DataStatus) -> List[Any]:
        """获取指定状态的股票列表"""
        return self.metadata_manager.get_stocks_with_status(status)
    
    def update_listed_date(self, symbol: str, exchange: Exchange, listed_date: datetime):
        """更新股票上市日期"""
        self.metadata_manager.update_listed_date(symbol, exchange, listed_date)
    
    def update_delisted_date(self, symbol: str, exchange: Exchange, delisted_date: datetime):
        """更新股票退市日期"""
        self.metadata_manager.update_delisted_date(symbol, exchange, delisted_date)
    
    def get_cache_summary(self) -> Dict[str, Any]:
        """获取缓存状态摘要"""
        # 扫描缓存
        scan_result = self.scan_lab_cache()
        
        # 获取各状态的股票数量
        missing_count = len(self.get_stocks_with_status(DataStatus.MISSING))
        partial_count = len(self.get_stocks_with_status(DataStatus.PARTIAL))
        complete_count = len(self.get_stocks_with_status(DataStatus.COMPLETE))
        
        return {
            "lab_path": self.lab_path,
            "scanned_daily": scan_result.get("scanned_daily", 0),
            "scanned_minute": scan_result.get("scanned_minute", 0),
            "stocks_by_status": {
                "missing": missing_count,
                "partial": partial_count,
                "complete": complete_count
            },
            "total_stocks": missing_count + partial_count + complete_count
        }
