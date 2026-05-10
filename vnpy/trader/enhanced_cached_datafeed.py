from typing import List, Optional, Callable, TypeVar, Generic, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging

from .datafeed import BaseDatafeed
from .object import HistoryRequest, BarData, TickData
from .constant import Interval, Exchange
from .locale import _
from .cache_backend import BaseCacheBackend, T
from .parquet_cache_backend import ParquetCacheBackend
from .database import get_database
from .stock_metadata import StockMetadataManager, DataStatus

logger = logging.getLogger(__name__)


class EnhancedCachedDatafeedWrapper(BaseDatafeed):
    """
    增强版缓存数据服务包装器，针对沪深300成分股回测优化
    
    主要功能：
    1. 集成股票元信息管理（上市/退市时间）
    2. 查询前检查是否跨越上市/退市时间点
    3. 实现数据库和parquet缓存的一致性检查
    4. 避免重复获取不存在的数据（未上市股票）
    5. 记录数据获取失败状态
    """
    
    def __init__(self, network_datafeed: BaseDatafeed, 
                 cache_backend: Optional[BaseCacheBackend[T]] = None):
        """
        初始化增强版缓存数据服务包装器
        
        Parameters:
            network_datafeed: 网络数据服务
            cache_backend: 缓存后端实现（默认使用ParquetCacheBackend）
        """
        self.network_datafeed = network_datafeed
        self.cache_backend = cache_backend or ParquetCacheBackend()
        self.metadata_manager = StockMetadataManager()
        self.inited = False
        
        # 缓存设置
        self.min_cache_length = 10
        self.max_fetch_attempts = 3  # 最大获取尝试次数
        
        # 异步任务管理
        self._cache_tasks: List[asyncio.Task] = []
        
        # 一致性检查设置
        self.enable_consistency_check = True
        self.consistency_warning_count = 0
        self.max_consistency_warnings = 10
    
    def init(self, output: Callable = print) -> bool:
        """
        初始化网络数据服务、缓存后端和元信息管理器
        """
        output(_("Initializing enhanced cached datafeed wrapper..."))
        
        # 初始化网络数据服务
        if hasattr(self.network_datafeed, 'init'):
            network_init = self.network_datafeed.init(output)
            if not network_init:
                output(_("Warning: Network datafeed initialization failed"))
        
        # 初始化缓存后端
        cache_init = self.cache_backend.init()
        if not cache_init:
            output(_("Warning: Cache backend initialization failed"))
        
        # 元信息管理器不需要额外初始化（在构造函数中完成）
        
        self.inited = True
        output(_("Enhanced cached datafeed wrapper initialized successfully"))
        return True
    
    def _validate_request(self, req: HistoryRequest, output: Callable = print) -> Dict[str, Any]:
        """
        验证请求的有效性，检查上市/退市时间
        
        Returns:
            dict: 验证结果
                - valid: bool - 是否有效
                - should_skip: bool - 是否应该跳过（完全没有数据）
                - actual_req: HistoryRequest - 调整后的请求
                - metadata: StockMetadata - 股票元信息
                - message: str - 说明信息
        """
        symbol = req.symbol
        exchange = req.exchange
        start = req.start
        end = req.end or datetime.now()
        
        # 获取股票元信息
        metadata = self.metadata_manager.get_metadata(symbol, exchange)
        
        # 检查日期范围
        check_result = self.metadata_manager.check_date_range(symbol, exchange, start, end)
        
        if not check_result["valid"]:
            output(f"[SKIP] {symbol}.{exchange} 请求时间范围无效: {check_result['message']}")
            return {
                "valid": False,
                "should_skip": True,
                "actual_req": None,
                "metadata": metadata,
                "message": check_result["message"]
            }
        
        # 检查是否需要调整请求时间
        needs_adjustment = False
        actual_start = start
        actual_end = end
        
        if check_result["before_listed"]:
            actual_start = check_result["actual_start"]
            needs_adjustment = True
        
        if check_result["after_delisted"]:
            actual_end = check_result["actual_end"]
            needs_adjustment = True
        
        # 检查是否有足够的获取尝试次数
        if metadata and metadata.fetch_attempts >= self.max_fetch_attempts:
            if metadata.data_status in [DataStatus.MISSING, DataStatus.FETCH_FAILED]:
                output(f"[SKIP] {symbol}.{exchange} 已达到最大获取尝试次数 {self.max_fetch_attempts}")
                return {
                    "valid": False,
                    "should_skip": True,
                    "actual_req": None,
                    "metadata": metadata,
                    "message": f"已达到最大获取尝试次数 {self.max_fetch_attempts}"
                }
        
        # 创建调整后的请求
        if needs_adjustment:
            actual_req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=req.interval,
                start=actual_start,
                end=actual_end
            )
            output(f"[ADJUST] {symbol}.{exchange} 请求时间调整: {start}~{end} -> {actual_start}~{actual_end}")
        else:
            actual_req = req
        
        return {
            "valid": True,
            "should_skip": False,
            "actual_req": actual_req,
            "metadata": metadata,
            "message": check_result["message"]
        }
    
    def _check_cache_consistency(self, req: HistoryRequest, output: Callable = print) -> bool:
        """
        检查数据库和parquet缓存的一致性
        
        Returns:
            bool: True表示一致，False表示不一致
        """
        if not self.enable_consistency_check:
            return True
        
        if self.consistency_warning_count >= self.max_consistency_warnings:
            return True  # 达到警告上限，不再检查
        
        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        
        result = self.metadata_manager.validate_cache_consistency(symbol, exchange, interval)
        
        if not result["consistent"]:
            self.consistency_warning_count += 1
            warnings = "\n  - ".join(result["issues"])
            output(f"[WARNING] {symbol}.{exchange} 缓存一致性检查失败:")
            output(f"  - {warnings}")
            
            # 详细日志记录
            if result["db_overview"]:
                db = result["db_overview"]
                output(f"    数据库缓存: {db.count}条记录, {db.start} ~ {db.end}")
            if result["parquet_overview"]:
                pq = result["parquet_overview"]
                output(f"    Parquet缓存: {pq['start']} ~ {pq['end']}")
        
        return result["consistent"]
    
    def _should_fetch_from_network(self, req: HistoryRequest, cache_data: List[Any], 
                                  output: Callable = print) -> bool:
        """
        判断是否需要从网络获取数据
        
        Returns:
            bool: True表示需要从网络获取
        """
        if not cache_data:
            return True
        
        start = req.start
        end = req.end or datetime.now()
        
        if isinstance(cache_data[0], BarData):
            cache_start = cache_data[0].datetime
            cache_end = cache_data[-1].datetime
        elif isinstance(cache_data[0], TickData):
            cache_start = cache_data[0].datetime
            cache_end = cache_data[-1].datetime
        else:
            return True
        
        # 检查缓存是否覆盖请求范围
        if cache_start > start or cache_end < end:
            output(f"缓存不完整: 请求 {start}~{end}, 缓存 {cache_start}~{cache_end}")
            return True
        
        return False
    
    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> List[BarData]:
        """
        查询K线历史数据（增强版，支持上市/退市时间检查和一致性验证）
        """
        if not self.inited:
            self.init(output)
        
        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        original_start = req.start
        original_end = req.end or datetime.now()
        
        output(f"查询K线数据: {symbol}.{exchange.value} [{interval.value}] {original_start} ~ {original_end}")
        
        # Step 1: 验证请求（检查上市/退市时间）
        validation = self._validate_request(req, output)
        if not validation["valid"]:
            if validation["should_skip"]:
                output(f"返回空数据列表（请求无效）")
                return []
            actual_req = validation["actual_req"]
        else:
            actual_req = validation["actual_req"]
        
        # Step 2: 检查缓存一致性
        self._check_cache_consistency(actual_req, output)
        
        # Step 3: 从缓存加载数据
        cache_bars: List[BarData] = self.cache_backend.load_data(actual_req)
        
        if cache_bars:
            cache_start = cache_bars[0].datetime
            cache_end = cache_bars[-1].datetime
            output(f"从缓存加载 {len(cache_bars)} 条数据: {cache_start} ~ {cache_end}")
        else:
            cache_start = None
            cache_end = None
            output("缓存中无数据")
        
        # Step 4: 判断是否需要从网络获取
        need_network_query = self._should_fetch_from_network(actual_req, cache_bars, output)
        
        if need_network_query:
            # 计算需要获取的时间范围
            network_start = actual_req.start
            network_end = actual_req.end or datetime.now()
            
            if cache_start and cache_start > network_start:
                # 缓存起始晚于请求起始，需要获取前面部分
                pass  # 使用network_start即可
            elif cache_end:
                # 从缓存结束之后开始获取
                network_start = cache_end + timedelta(days=1)
            
            # 检查是否有重叠或无效范围
            if network_start > network_end:
                output(f"网络查询范围无效: {network_start} > {network_end}")
                need_network_query = False
        
        # Step 5: 从网络获取数据
        net_bars: List[BarData] = []
        fetch_success = False
        
        if need_network_query:
            net_req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=network_start,
                end=network_end
            )
            
            output(f"从网络查询: {network_start} ~ {network_end}")
            
            try:
                net_bars = self.network_datafeed.query_bar_history(net_req, output)
                fetch_success = True
                
                if net_bars:
                    output(f"从网络获取 {len(net_bars)} 条数据")
                else:
                    output("网络查询返回空数据（可能跨越上市/退市时间点）")
            
            except Exception as e:
                fetch_success = False
                output(f"网络查询失败: {e}")
                
                # 标记获取失败
                self.metadata_manager.mark_fetch_failed(symbol, exchange, str(e))
                output(f"标记 {symbol}.{exchange} 获取失败")
        
        # Step 6: 异步缓存网络数据
        if fetch_success and net_bars and len(net_bars) >= self.min_cache_length:
            task = asyncio.create_task(self._async_cache_bars(net_bars, output))
            self._cache_tasks.append(task)
            task.add_done_callback(lambda t: self._cache_tasks.remove(t) if t in self._cache_tasks else None)
        
        # Step 7: 更新元信息
        self.metadata_manager.update_metadata_from_fetch(
            symbol=exchange,
            exchange=exchange,
            req=actual_req,
            fetched_bars=net_bars if fetch_success else [],
            fetch_success=fetch_success
        )
        
        # 如果网络获取失败且缓存有数据，只返回缓存数据
        if not fetch_success and cache_bars:
            output(f"网络获取失败，返回缓存数据（{len(cache_bars)}条）")
            return cache_bars
        
        # Step 8: 合并并返回数据
        merged_bars = self._merge_bars(cache_bars, net_bars)
        
        if merged_bars:
            merged_start = merged_bars[0].datetime
            merged_end = merged_bars[-1].datetime
            output(f"返回合并数据 {len(merged_bars)} 条: {merged_start} ~ {merged_end}")
        else:
            output("返回空数据列表")
        
        return merged_bars
    
    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> List[TickData]:
        """
        查询Tick历史数据（增强版，支持上市/退市时间检查和一致性验证）
        """
        if not self.inited:
            self.init(output)
        
        symbol = req.symbol
        exchange = req.exchange
        original_start = req.start
        original_end = req.end or datetime.now()
        
        output(f"查询Tick数据: {symbol}.{exchange.value} {original_start} ~ {original_end}")
        
        # Step 1: 验证请求
        validation = self._validate_request(req, output)
        if not validation["valid"]:
            if validation["should_skip"]:
                output(f"返回空数据列表（请求无效）")
                return []
            actual_req = validation["actual_req"]
        else:
            actual_req = validation["actual_req"]
        
        # Step 2: 从缓存加载数据
        cache_ticks: List[TickData] = self.cache_backend.load_data(actual_req)
        
        if cache_ticks:
            cache_start = cache_ticks[0].datetime
            cache_end = cache_ticks[-1].datetime
            output(f"从缓存加载 {len(cache_ticks)} 条数据: {cache_start} ~ {cache_end}")
        else:
            cache_start = None
            cache_end = None
            output("缓存中无数据")
        
        # Step 3: 判断是否需要从网络获取
        need_network_query = self._should_fetch_from_network(actual_req, cache_ticks, output)
        
        if need_network_query:
            network_start = actual_req.start
            network_end = actual_req.end or datetime.now()
            
            if cache_end:
                network_start = cache_end + timedelta(milliseconds=1)
            
            if network_start > network_end:
                need_network_query = False
        
        # Step 4: 从网络获取数据
        net_ticks: List[TickData] = []
        fetch_success = False
        
        if need_network_query:
            net_req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                start=network_start,
                end=network_end
            )
            
            output(f"从网络查询: {network_start} ~ {network_end}")
            
            try:
                net_ticks = self.network_datafeed.query_tick_history(net_req, output)
                fetch_success = True
                
                if net_ticks:
                    output(f"从网络获取 {len(net_ticks)} 条数据")
                else:
                    output("网络查询返回空数据（可能跨越上市/退市时间点）")
            
            except Exception as e:
                fetch_success = False
                output(f"网络查询失败: {e}")
                self.metadata_manager.mark_fetch_failed(symbol, exchange, str(e))
        
        # Step 5: 异步缓存网络数据
        if fetch_success and net_ticks and len(net_ticks) >= self.min_cache_length:
            task = asyncio.create_task(self._async_cache_ticks(net_ticks, output))
            self._cache_tasks.append(task)
            task.add_done_callback(lambda t: self._cache_tasks.remove(t) if t in self._cache_tasks else None)
        
        # Step 6: 更新元信息
        self.metadata_manager.update_metadata_from_fetch(
            symbol=symbol,
            exchange=exchange,
            req=actual_req,
            fetched_bars=net_ticks if fetch_success else [],
            fetch_success=fetch_success
        )
        
        # 如果网络获取失败且缓存有数据，只返回缓存数据
        if not fetch_success and cache_ticks:
            output(f"网络获取失败，返回缓存数据（{len(cache_ticks)}条）")
            return cache_ticks
        
        # Step 7: 合并并返回数据
        merged_ticks = self._merge_ticks(cache_ticks, net_ticks)
        
        if merged_ticks:
            merged_start = merged_ticks[0].datetime
            merged_end = merged_ticks[-1].datetime
            output(f"返回合并数据 {len(merged_ticks)} 条: {merged_start} ~ {merged_end}")
        else:
            output("返回空数据列表")
        
        return merged_ticks
    
    async def _async_cache_bars(self, bars: List[BarData], output: Callable = print) -> bool:
        """异步缓存K线数据"""
        try:
            output(f"异步缓存 {len(bars)} 条K线数据")
            
            # 保存到缓存后端
            result = self.cache_backend.save_data(bars)
            
            if result and bars:
                # 更新parquet元信息
                first_bar = bars[0]
                last_bar = bars[-1]
                self.metadata_manager.update_parquet_metadata(
                    symbol=first_bar.symbol,
                    exchange=first_bar.exchange,
                    interval=first_bar.interval,
                    start=first_bar.datetime,
                    end=last_bar.datetime
                )
                
                # 同时保存到数据库
                db = get_database()
                db_result = db.save_bar_data(bars)
                if db_result:
                    self.metadata_manager.update_db_metadata(
                        symbol=first_bar.symbol,
                        exchange=first_bar.exchange,
                        interval=first_bar.interval,
                        start=first_bar.datetime,
                        end=last_bar.datetime
                    )
            
            if result:
                output(f"成功缓存 {len(bars)} 条K线数据")
            else:
                output(f"缓存K线数据失败")
            
            return result
        except Exception as e:
            output(f"缓存K线数据异常: {e}")
            return False
    
    async def _async_cache_ticks(self, ticks: List[TickData], output: Callable = print) -> bool:
        """异步缓存Tick数据"""
        try:
            output(f"异步缓存 {len(ticks)} 条Tick数据")
            
            # 保存到缓存后端
            result = self.cache_backend.save_data(ticks)
            
            if result and ticks:
                # 更新parquet元信息
                first_tick = ticks[0]
                last_tick = ticks[-1]
                self.metadata_manager.update_parquet_metadata(
                    symbol=first_tick.symbol,
                    exchange=first_tick.exchange,
                    interval=None,  # Tick数据无周期
                    start=first_tick.datetime,
                    end=last_tick.datetime
                )
                
                # 同时保存到数据库
                db = get_database()
                db_result = db.save_tick_data(ticks)
                if db_result:
                    self.metadata_manager.update_db_metadata(
                        symbol=first_tick.symbol,
                        exchange=first_tick.exchange,
                        interval=None,
                        start=first_tick.datetime,
                        end=last_tick.datetime
                    )
            
            if result:
                output(f"成功缓存 {len(ticks)} 条Tick数据")
            else:
                output(f"缓存Tick数据失败")
            
            return result
        except Exception as e:
            output(f"缓存Tick数据异常: {e}")
            return False
    
    def _merge_bars(self, cache_bars: List[BarData], net_bars: List[BarData]) -> List[BarData]:
        """合并K线数据"""
        bar_dict = {}
        
        for bar in cache_bars:
            bar_dict[bar.datetime] = bar
        
        for bar in net_bars:
            bar_dict[bar.datetime] = bar
        
        return sorted(bar_dict.values(), key=lambda x: x.datetime)
    
    def _merge_ticks(self, cache_ticks: List[TickData], net_ticks: List[TickData]) -> List[TickData]:
        """合并Tick数据"""
        tick_dict = {}
        
        for tick in cache_ticks:
            tick_dict[tick.datetime] = tick
        
        for tick in net_ticks:
            tick_dict[tick.datetime] = tick
        
        return sorted(tick_dict.values(), key=lambda x: x.datetime)
    
    async def wait_cache_tasks_complete(self, timeout: Optional[float] = None) -> bool:
        """等待所有缓存任务完成"""
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
        """取消所有缓存任务"""
        for task in self._cache_tasks:
            if not task.done():
                task.cancel()
        self._cache_tasks.clear()
    
    def get_stocks_status_summary(self) -> Dict[str, Any]:
        """获取股票状态汇总"""
        all_metadata = self.metadata_manager.get_all_metadata()
        
        summary = {
            "total_stocks": len(all_metadata),
            "status_counts": {},
            "detailed": []
        }
        
        for status in DataStatus:
            count = sum(1 for m in all_metadata if m.data_status == status)
            summary["status_counts"][status.value] = count
        
        # 提取详细信息
        for metadata in all_metadata:
            summary["detailed"].append({
                "symbol": metadata.symbol,
                "exchange": metadata.exchange.value if metadata.exchange else None,
                "listed_date": metadata.listed_date,
                "delisted_date": metadata.delisted_date,
                "data_status": metadata.data_status.value,
                "fetch_attempts": metadata.fetch_attempts,
                "last_fetch_time": metadata.last_fetch_time
            })
        
        return summary


# 工厂函数
T = TypeVar('T', BarData, TickData)

def create_enhanced_cached_datafeed(
    network_datafeed: BaseDatafeed, 
    cache_backend: Optional[BaseCacheBackend[T]] = None
) -> EnhancedCachedDatafeedWrapper:
    """
    创建增强版缓存数据服务
    
    Parameters:
        network_datafeed: 网络数据服务
        cache_backend: 缓存后端实现
    
    Returns:
        EnhancedCachedDatafeedWrapper: 增强版缓存数据服务
    """
    return EnhancedCachedDatafeedWrapper(network_datafeed, cache_backend)