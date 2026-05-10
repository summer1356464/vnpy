#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vnpy-tx: 基于腾讯财经API的行情数据源模块
"""

import sys
from datetime import datetime
from typing import List, Callable

import akshare as ak

from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.object import HistoryRequest, BarData, TickData
from vnpy.trader.constant import Exchange, Interval

__version__ = "0.1.0"


class Datafeed(BaseDatafeed):
    """
    基于腾讯财经API的行情数据源实现
    使用AKShare库调用腾讯财经接口获取A股历史数据
    """
    
    def __init__(self) -> None:
        """初始化数据feed"""
        self.akshare = None
        self.inited = False
    
    def init(self, output: Callable = print) -> bool:
        """
        初始化数据源服务连接
        
        Args:
            output: 输出回调函数
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 使用全局导入的akshare模块
            self.akshare = ak
            self.inited = True
            output("腾讯财经行情数据源初始化成功")
            return True
        except ImportError:
            output("导入AKShare失败，请运行 pip install akshare 尝试安装")
            return False
        except Exception as e:
            output(f"初始化AKShare失败：{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> List[BarData]:
        """
        查询历史K线数据
        
        Args:
            req: 历史数据请求对象
            output: 输出回调函数
            
        Returns:
            List[BarData]: K线数据列表
        """
        if not self.inited:
            if not self.init(output):
                return []
        
        try:
            # 检查是否支持该时间周期
            if req.interval != Interval.DAILY:
                output(f"不支持的K线周期：{req.interval.value}，腾讯财经API仅支持日线数据")
                return []
                
            output(f"正在查询{req.symbol}.{req.exchange.value}的{req.interval.value}K线数据")
            
            # 转换为腾讯财经所需的代码格式（sh600000或sz000001）
            if req.exchange == Exchange.SSE:
                ak_symbol = f"sh{req.symbol}"
            elif req.exchange == Exchange.SZSE:
                ak_symbol = f"sz{req.symbol}"
            else:
                output(f"不支持的交易所：{req.exchange}")
                return []
            
            # 转换时间格式
            start_date = req.start.strftime("%Y%m%d")
            end_date = req.end.strftime("%Y%m%d") if req.end else datetime.now().strftime("%Y%m%d")
            
            # 下载历史数据
            df = self.akshare.stock_zh_a_hist_tx(
                symbol=ak_symbol,
                start_date=start_date,
                end_date=end_date,
                adjust="hfq"  # 后复权
            )
            
            if df.empty:
                output(f"未获取到{req.symbol}.{req.exchange.value}的K线数据")
                return []
            
            output(f"成功获取{len(df)}条{req.interval.value}K线数据")
            
            # 转换为BarData列表
            bars: List[BarData] = []
            for _, row in df.iterrows():
                # 腾讯财经返回的字段名：date, open, close, high, low, amount
                # date字段已经是datetime.date类型，不需要再转换
                bar = BarData(
                    symbol=req.symbol,
                    exchange=req.exchange,
                    datetime=datetime.combine(row["date"], datetime.min.time()),  # 转换为datetime.datetime类型
                    interval=req.interval,
                    volume=0,  # 腾讯财经不直接提供成交量，需要计算
                    turnover=float(row["amount"]),
                    open_interest=0,
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                    gateway_name="TX"
                )
                
                # 根据成交额和收盘价计算成交量（成交量 = 成交额 / 收盘价，A股交易单位为股）
                if bar.close_price > 0:
                    bar.volume = round(bar.turnover / bar.close_price, 0)
                
                bars.append(bar)
            
            return bars
            
        except Exception as e:
            output(f"查询K线数据失败：{e}")
            import traceback
            traceback.print_exc()
            return []
    
    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> List[TickData]:
        """
        查询历史Tick数据
        
        注意：腾讯财经API不提供历史Tick数据，此方法返回空列表
        
        Args:
            req: 历史数据请求对象
            output: 输出回调函数
            
        Returns:
            List[TickData]: Tick数据列表（为空）
        """
        output("腾讯财经API不提供历史Tick数据")
        return []