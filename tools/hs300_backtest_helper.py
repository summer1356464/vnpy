#!/usr/bin/env python3
"""
沪深300成分股回测辅助工具

功能：
1. 获取沪深300成分股列表
2. 批量检查成分股上市/退市状态
3. 根据回测时间窗口过滤有效股票
4. 管理股票元信息
5. 提供增强版数据服务

Usage:
    from tools.hs300_backtest_helper import HS300BacktestHelper
    
    helper = HS300BacktestHelper()
    valid_stocks = helper.get_valid_stocks_for_backtest(
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2024, 1, 1)
    )
    print(f"有效股票数量: {len(valid_stocks)}")
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.cached_datafeed import (
    EnhancedCachedDatafeedWrapper,
    create_enhanced_cached_datafeed,
    StockMetadataManager,
    DataStatus
)


class HS300BacktestHelper:
    """
    沪深300回测辅助工具类
    """
    
    def __init__(self, cache_root: str = "./data_cache"):
        """
        初始化辅助工具
        
        Parameters:
            cache_root: 缓存根目录
        """
        self.cache_root = Path(cache_root)
        self.cache_root.mkdir(exist_ok=True, parents=True)
        
        self.metadata_manager = StockMetadataManager()
        self._cached_datafeed = None
        
        # 加载股票基础信息
        self.stock_info_cache: Dict[str, dict] = {}
    
    @property
    def cached_datafeed(self):
        """获取增强版缓存数据服务"""
        if self._cached_datafeed is None:
            network_datafeed = get_datafeed()
            self._cached_datafeed = create_enhanced_cached_datafeed(network_datafeed)
            self._cached_datafeed.init(self._log)
        return self._cached_datafeed
    
    def _log(self, message: str):
        """日志输出"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")
    
    def get_hs300_constituents(self, update_cache: bool = False) -> List[str]:
        """
        获取沪深300成分股列表
        
        Parameters:
            update_cache: 是否强制更新缓存
        
        Returns:
            list: 成分股列表，格式为 "000001.SZSE"
        """
        cache_file = self.cache_root / "hs300_constituents.txt"
        
        if cache_file.exists() and not update_cache:
            with open(cache_file, "r") as f:
                stocks = [line.strip() for line in f if line.strip()]
            self._log(f"从缓存加载沪深300成分股 {len(stocks)} 只")
            return stocks
        
        try:
            # 使用akshare获取沪深300成分股
            df = ak.index_stock_cons(symbol="000300")
            
            stocks = []
            for _, row in df.iterrows():
                code = str(row["品种代码"]).zfill(6)
                if code.startswith("6"):
                    # 沪市股票
                    stocks.append(f"{code}.{Exchange.SSE.value}")
                else:
                    # 深市股票
                    stocks.append(f"{code}.{Exchange.SZSE.value}")
            
            # 保存到缓存
            with open(cache_file, "w") as f:
                for stock in stocks:
                    f.write(f"{stock}\n")
            
            self._log(f"成功获取沪深300成分股 {len(stocks)} 只")
            return stocks
        
        except Exception as e:
            self._log(f"获取沪深300成分股失败: {e}")
            # 返回备用列表（部分成分股）
            return self._get_fallback_constituents()
    
    def _get_fallback_constituents(self) -> List[str]:
        """返回备用成分股列表"""
        return [
            "000001.SZSE", "000002.SZSE", "000008.SZSE", "000009.SZSE", "000012.SZSE",
            "000021.SZSE", "000024.SZSE", "000027.SZSE", "000039.SZSE", "000046.SZSE",
            "600000.SSE", "600004.SSE", "600006.SSE", "600007.SSE", "600008.SSE",
            "600009.SSE", "600010.SSE", "600011.SSE", "600012.SSE", "600015.SSE"
        ]
    
    def parse_vt_symbol(self, vt_symbol: str) -> tuple:
        """
        解析vt_symbol
        
        Returns:
            tuple: (symbol, exchange)
        """
        parts = vt_symbol.split(".")
        if len(parts) == 2:
            return parts[0], Exchange(parts[1])
        return vt_symbol, Exchange.SSE  # 默认沪市
    
    def get_stock_metadata(self, vt_symbol: str) -> Optional[dict]:
        """
        获取单只股票的元信息
        
        Parameters:
            vt_symbol: 股票代码，格式如 "000001.SZSE"
        
        Returns:
            dict: 股票元信息
        """
        symbol, exchange = self.parse_vt_symbol(vt_symbol)
        metadata = self.metadata_manager.get_metadata(symbol, exchange)
        
        if not metadata:
            return None
        
        return {
            "symbol": metadata.symbol,
            "exchange": metadata.exchange.value if metadata.exchange else None,
            "listed_date": metadata.listed_date,
            "delisted_date": metadata.delisted_date,
            "first_trade_date": metadata.first_trade_date,
            "last_trade_date": metadata.last_trade_date,
            "data_status": metadata.data_status.value,
            "fetch_attempts": metadata.fetch_attempts,
            "last_fetch_time": metadata.last_fetch_time,
            "parquet_start": metadata.parquet_start,
            "parquet_end": metadata.parquet_end,
            "db_start": metadata.db_start,
            "db_end": metadata.db_end
        }
    
    def get_valid_stocks_for_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        min_data_days: int = 30,
        update_metadata: bool = True
    ) -> List[dict]:
        """
        获取在回测时间窗口内有效的股票列表
        
        有效条件：
        1. 在回测开始前已上市（或在回测期间上市但有足够数据）
        2. 在回测结束后仍未退市（或在回测期间退市但有足够数据）
        3. 有足够的历史数据
        
        Parameters:
            start_date: 回测开始时间
            end_date: 回测结束时间
            min_data_days: 最小数据天数要求
            update_metadata: 是否更新元信息
        
        Returns:
            list: 有效股票列表，包含元信息
        """
        stocks = self.get_hs300_constituents()
        valid_stocks = []
        
        self._log(f"开始检查 {len(stocks)} 只股票的有效性...")
        
        for vt_symbol in stocks:
            symbol, exchange = self.parse_vt_symbol(vt_symbol)
            metadata = self.metadata_manager.get_metadata(symbol, exchange)
            
            # 检查上市/退市时间
            if metadata and metadata.listed_date:
                listed_date = metadata.listed_date
            else:
                listed_date = None  # 未知上市时间
            
            if metadata and metadata.delisted_date:
                delisted_date = metadata.delisted_date
            else:
                delisted_date = None  # 未知或未退市
            
            # 判断是否有效
            is_valid = True
            reason = ""
            
            # 检查是否在回测结束后才上市
            if listed_date and listed_date > end_date:
                is_valid = False
                reason = "回测结束后才上市"
            # 检查是否在回测开始前已退市
            elif delisted_date and delisted_date < start_date:
                is_valid = False
                reason = "回测开始前已退市"
            
            # 对于上市时间未知的股票，标记为需要验证
            if listed_date is None and not reason:
                reason = "上市时间未知，需要验证"
            
            # 检查数据完整性（如果有记录）
            if metadata and is_valid:
                if metadata.first_trade_date and metadata.last_trade_date:
                    data_days = (metadata.last_trade_date - metadata.first_trade_date).days
                    if data_days < min_data_days:
                        reason = f"数据不足（仅{data_days}天）"
            
            valid_stocks.append({
                "vt_symbol": vt_symbol,
                "symbol": symbol,
                "exchange": exchange.value,
                "listed_date": listed_date,
                "delisted_date": delisted_date,
                "is_valid": is_valid,
                "reason": reason,
                "data_status": metadata.data_status.value if metadata else DataStatus.MISSING.value,
                "fetch_attempts": metadata.fetch_attempts if metadata else 0
            })
        
        self._log(f"检查完成，有效股票 {sum(1 for s in valid_stocks if s['is_valid'])} 只")
        self._log(f"无效股票 {sum(1 for s in valid_stocks if not s['is_valid'])} 只")
        
        return valid_stocks
    
    def update_stock_metadata_batch(self, vt_symbols: List[str], 
                                    test_start: datetime, test_end: datetime):
        """
        批量更新股票元信息
        
        Parameters:
            vt_symbols: 股票列表
            test_start: 测试起始时间
            test_end: 测试结束时间
        """
        self._log(f"开始批量更新 {len(vt_symbols)} 只股票的元信息...")
        
        for i, vt_symbol in enumerate(vt_symbols, 1):
            symbol, exchange = self.parse_vt_symbol(vt_symbol)
            
            self._log(f"[{i}/{len(vt_symbols)}] 检查 {vt_symbol}")
            
            # 创建请求
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.DAILY,
                start=test_start,
                end=test_end
            )
            
            # 查询数据（会自动更新元信息）
            try:
                bars = self.cached_datafeed.query_bar_history(req, self._log)
                
                if bars:
                    first_bar = bars[0]
                    last_bar = bars[-1]
                    
                    # 更新实际交易日期
                    metadata = self.metadata_manager.get_metadata(symbol, exchange)
                    if metadata:
                        # 如果请求时间之前没有数据，说明是在这段时间内上市的
                        if first_bar.datetime > test_start:
                            if not metadata.listed_date or first_bar.datetime < metadata.listed_date:
                                metadata.listed_date = first_bar.datetime
                            
                            self._log(f"  检测到上市时间: {metadata.listed_date}")
                        
                        self.metadata_manager.save_metadata(metadata)
                
            except Exception as e:
                self._log(f"  查询失败: {e}")
                self.metadata_manager.mark_fetch_failed(symbol, exchange, str(e))
        
        self._log("批量更新完成")
    
    def download_stock_data_batch(
        self,
        vt_symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: Interval = Interval.DAILY,
        skip_existing: bool = True
    ) -> Dict[str, int]:
        """
        批量下载股票数据
        
        Parameters:
            vt_symbols: 股票列表
            start_date: 起始时间
            end_date: 结束时间
            interval: 数据周期
            skip_existing: 是否跳过已有完整数据的股票
        
        Returns:
            dict: 下载结果统计
        """
        result = {
            "total": len(vt_symbols),
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "details": []
        }
        
        self._log(f"开始批量下载 {len(vt_symbols)} 只股票数据...")
        
        for i, vt_symbol in enumerate(vt_symbols, 1):
            symbol, exchange = self.parse_vt_symbol(vt_symbol)
            
            self._log(f"[{i}/{len(vt_symbols)}] 下载 {vt_symbol}")
            
            # 检查是否需要跳过
            if skip_existing:
                consistency = self.metadata_manager.validate_cache_consistency(symbol, exchange, interval)
                
                # 如果数据状态为COMPLETE且缓存完整，跳过
                metadata = self.metadata_manager.get_metadata(symbol, exchange)
                if (metadata and metadata.data_status == DataStatus.COMPLETE and
                    metadata.parquet_start and metadata.parquet_start <= start_date and
                    metadata.parquet_end and metadata.parquet_end >= end_date):
                    self._log(f"  跳过（数据已完整）")
                    result["skipped"] += 1
                    result["details"].append({
                        "vt_symbol": vt_symbol,
                        "status": "skipped",
                        "reason": "数据已完整"
                    })
                    continue
            
            # 下载数据
            try:
                req = HistoryRequest(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    start=start_date,
                    end=end_date
                )
                
                bars = self.cached_datafeed.query_bar_history(req, self._log)
                
                if bars:
                    self._log(f"  成功下载 {len(bars)} 条数据")
                    result["downloaded"] += 1
                    result["details"].append({
                        "vt_symbol": vt_symbol,
                        "status": "downloaded",
                        "count": len(bars)
                    })
                else:
                    self._log(f"  无数据返回（可能未上市）")
                    result["failed"] += 1
                    result["details"].append({
                        "vt_symbol": vt_symbol,
                        "status": "failed",
                        "reason": "无数据"
                    })
                
            except Exception as e:
                self._log(f"  下载失败: {e}")
                result["failed"] += 1
                result["details"].append({
                    "vt_symbol": vt_symbol,
                    "status": "failed",
                    "reason": str(e)
                })
        
        # 等待缓存任务完成
        import asyncio
        asyncio.run(self.cached_datafeed.wait_cache_tasks_complete(timeout=60))
        
        self._log(f"批量下载完成: 下载 {result['downloaded']} 只, 跳过 {result['skipped']} 只, 失败 {result['failed']} 只")
        
        return result
    
    def get_data_status_report(self) -> str:
        """
        获取数据状态报告
        
        Returns:
            str: 格式化的报告
        """
        summary = self.cached_datafeed.get_stocks_status_summary()
        
        report = [
            "=" * 60,
            "股票数据状态报告",
            "=" * 60,
            f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"总股票数: {summary['total_stocks']}",
            "",
            "状态分布:"
        ]
        
        for status, count in summary["status_counts"].items():
            percentage = (count / summary["total_stocks"] * 100) if summary["total_stocks"] > 0 else 0
            report.append(f"  {status}: {count} 只 ({percentage:.1f}%)")
        
        # 详细信息
        if summary["detailed"]:
            report.append("")
            report.append("详细信息:")
            report.append("-" * 60)
            report.append(f"{'股票代码':<15} {'上市日期':<12} {'退市日期':<12} {'状态':<10} {'尝试次数':<8}")
            report.append("-" * 60)
            
            for stock in summary["detailed"]:
                listed = stock["listed_date"].strftime("%Y-%m-%d") if stock["listed_date"] else "未知"
                delisted = stock["delisted_date"].strftime("%Y-%m-%d") if stock["delisted_date"] else "未退市"
                report.append(f"{stock['symbol']}.{stock['exchange']:<15} {listed:<12} {delisted:<12} {stock['data_status']:<10} {stock['fetch_attempts']:<8}")
        
        report.append("=" * 60)
        
        return "\n".join(report)


# 示例用法
if __name__ == "__main__":
    from datetime import datetime
    
    # 创建辅助工具
    helper = HS300BacktestHelper()
    
    # 获取沪深300成分股
    stocks = helper.get_hs300_constituents()
    print(f"沪深300成分股数量: {len(stocks)}")
    print(f"前5只: {stocks[:5]}")
    
    # 设置回测时间窗口
    backtest_start = datetime(2020, 1, 1)
    backtest_end = datetime(2024, 12, 31)
    
    # 获取有效股票
    valid_stocks = helper.get_valid_stocks_for_backtest(backtest_start, backtest_end)
    
    # 输出有效和无效股票
    print(f"\n有效股票: {sum(1 for s in valid_stocks if s['is_valid'])} 只")
    print(f"无效股票: {sum(1 for s in valid_stocks if not s['is_valid'])} 只")
    
    # 显示部分无效股票原因
    invalid_reasons = {}
    for stock in valid_stocks:
        if not stock['is_valid']:
            reason = stock['reason']
            invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
    
    print("\n无效原因分布:")
    for reason, count in invalid_reasons.items():
        print(f"  {reason}: {count} 只")
    
    # 下载数据（仅测试前5只）
    test_stocks = stocks[:5]
    print(f"\n测试下载前5只股票数据...")
    result = helper.download_stock_data_batch(
        test_stocks,
        backtest_start,
        backtest_end,
        skip_existing=True
    )
    
    # 打印状态报告
    print("\n" + helper.get_data_status_report())