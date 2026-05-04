#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试vnpy_tx模块的功能
"""

import sys
import os
from datetime import datetime

# 将当前目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.setting import SETTINGS

# 设置使用tx数据feed
SETTINGS["datafeed.name"] = "tx"
SETTINGS["datafeed.use_cache"] = False  # 测试时先禁用缓存

def test_query_bar_history():
    """测试查询K线历史数据"""
    print("=" * 60)
    print("测试查询K线历史数据")
    print("=" * 60)
    
    # 获取数据feed实例
    datafeed = get_datafeed()
    
    # 查询历史数据
    req = HistoryRequest(
        symbol="600000",
        exchange=Exchange.SSE,
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 12, 31)
    )
    
    print(f"查询参数：")
    print(f"  股票代码：{req.symbol}")
    print(f"  交易所：{req.exchange}")
    print(f"  时间周期：{req.interval}")
    print(f"  开始时间：{req.start}")
    print(f"  结束时间：{req.end}")
    
    bars = datafeed.query_bar_history(req)
    
    if bars:
        print(f"\n查询结果：")
        print(f"  获取到{len(bars)}条K线数据")
        print(f"  第一条数据：")
        print(f"    时间：{bars[0].datetime}")
        print(f"    开盘价：{bars[0].open_price}")
        print(f"    最高价：{bars[0].high_price}")
        print(f"    最低价：{bars[0].low_price}")
        print(f"    收盘价：{bars[0].close_price}")
        print(f"    成交量：{bars[0].volume}")
        print(f"    成交额：{bars[0].turnover}")
        print(f"  最后一条数据：")
        print(f"    时间：{bars[-1].datetime}")
        print(f"    收盘价：{bars[-1].close_price}")
        print(f"    成交量：{bars[-1].volume}")
        print(f"    成交额：{bars[-1].turnover}")
    else:
        print("\n未获取到数据")
    
    return len(bars) > 0

def test_query_tick_history():
    """测试查询Tick历史数据"""
    print("\n" + "=" * 60)
    print("测试查询Tick历史数据")
    print("=" * 60)
    
    # 获取数据feed实例
    datafeed = get_datafeed()
    
    # 查询历史数据
    req = HistoryRequest(
        symbol="600000",
        exchange=Exchange.SSE,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 12, 31)
    )
    
    ticks = datafeed.query_tick_history(req)
    
    if ticks:
        print(f"获取到{len(ticks)}条Tick数据")
    else:
        print("未获取到Tick数据（腾讯财经API不提供历史Tick数据）")
    
    return True

def test_multiple_symbols():
    """测试查询多个股票的历史数据"""
    print("\n" + "=" * 60)
    print("测试查询多个股票的历史数据")
    print("=" * 60)
    
    # 获取数据feed实例
    datafeed = get_datafeed()
    
    # 测试股票列表
    symbols = ["600000", "600004"]
    
    for symbol in symbols:
        print(f"\n查询股票：{symbol}.SSE")
        req = HistoryRequest(
            symbol=symbol,
            exchange=Exchange.SSE,
            interval=Interval.DAILY,
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 31)
        )
        
        bars = datafeed.query_bar_history(req)
        print(f"  获取到{len(bars)}条数据")
    
    return True

def test_interval_check():
    """测试时间周期检查功能"""
    print("\n" + "=" * 60)
    print("测试时间周期检查功能")
    print("=" * 60)
    
    # 获取数据feed实例
    datafeed = get_datafeed()
    
    # 测试不支持的时间周期（分钟线）
    print("\n测试查询分钟线数据（应该失败）：")
    req = HistoryRequest(
        symbol="600000",
        exchange=Exchange.SSE,
        interval=Interval.MINUTE,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 31)
    )
    
    bars = datafeed.query_bar_history(req)
    if len(bars) == 0:
        print("  ✓ 正确拒绝了不支持的时间周期")
        return True
    else:
        print("  ✗ 没有正确拒绝不支持的时间周期")
        return False

if __name__ == "__main__":
    print("开始测试vnpy_tx模块...")
    print()
    
    # 测试各个功能
    test1 = test_query_bar_history()
    test2 = test_query_tick_history()
    test3 = test_multiple_symbols()
    test4 = test_interval_check()
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"查询K线历史数据：{'✓ 成功' if test1 else '✗ 失败'}")
    print(f"查询Tick历史数据：{'✓ 成功' if test2 else '✗ 失败'}")
    print(f"查询多个股票数据：{'✓ 成功' if test3 else '✗ 失败'}")
    print(f"时间周期检查功能：{'✓ 成功' if test4 else '✗ 失败'}")
    
    if test1 and test2 and test3 and test4:
        print("\n🎉 所有测试通过！vnpy_tx模块功能正常")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查模块实现")
        sys.exit(1)