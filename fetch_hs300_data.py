#!/usr/bin/env python3
"""
批量下载沪深300成分股数据并保存到本地parquet文件
"""
import asyncio
from datetime import datetime, timedelta
import os
import sys

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.setting import SETTINGS
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest
from vnpy.trader.utility import extract_vt_symbol
from vnpy.alpha.lab import AlphaLab

from get_hs300_constituents import get_hs300_constituents


# 设置使用tx数据源和缓存
SETTINGS["datafeed.name"] = "tx"
SETTINGS["datafeed.use_cache"] = True


async def fetch_single_stock_data(datafeed, lab, vt_symbol, start_date, end_date, interval):
    """
    下载单只股票的数据
    
    Args:
        datafeed: 数据源实例
        lab: AlphaLab实例
        vt_symbol: 标的代码
        start_date: 开始日期
        end_date: 结束日期
        interval: 时间周期
    
    Returns:
        bool: 是否成功
    """
    try:
        # 解析symbol和exchange
        symbol, exchange = extract_vt_symbol(vt_symbol)
        
        # 创建历史数据请求
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=start_date,
            end=end_date
        )
        
        # 查询数据
        bars = datafeed.query_bar_history(req)
        
        if bars:
            print(f"  ✓ 成功获取 {len(bars)} 条数据")
            # 保存到本地文件
            lab.save_bar_data(bars)
            return True
        else:
            print(f"  ✗ 未获取到数据")
            return False
            
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        return False


async def fetch_hs300_data(start_date: datetime, end_date: datetime, interval: Interval = Interval.DAILY):
    """
    批量下载沪深300成分股数据
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        interval: 时间周期
    """
    # 获取沪深300成分股列表
    hs300_stocks = get_hs300_constituents()
    print(f"沪深300成分股数量: {len(hs300_stocks)}")
    
    # 初始化数据源
    datafeed = get_datafeed()
    success = datafeed.init()
    if not success:
        print("数据源初始化失败")
        return
    
    # 创建AlphaLab实例
    lab_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alpha_lab")
    lab = AlphaLab(lab_path)
    
    # 批量下载数据
    success_count = 0
    total_count = len(hs300_stocks)
    
    # 使用异步方式下载
    # 先下载前20只股票进行测试
    download_count = 20
    for i, vt_symbol in enumerate(hs300_stocks[:download_count]):
        print(f"\n正在下载 {i+1}/{total_count}: {vt_symbol}")
        success = await fetch_single_stock_data(datafeed, lab, vt_symbol, start_date, end_date, interval)
        if success:
            success_count += 1
    
    print(f"\n下载完成: {success_count}/{min(download_count, total_count)} 只股票成功")


if __name__ == "__main__":
    # 设置下载时间范围
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    # 下载日线数据
    asyncio.run(fetch_hs300_data(start_date, end_date, Interval.DAILY))
