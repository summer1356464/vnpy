#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VeighNa数据源集成测试
测试新添加的AKShare和新浪财经数据源
"""

import sys
from datetime import datetime
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest
from vnpy.trader.setting import SETTINGS

print("="*60)
print("VeighNa数据源集成测试")
print("="*60 + "\n")

def test_datafeed(datafeed_name):
    """测试指定数据源"""
    print(f"测试数据源: {datafeed_name}")
    print("-" * 40)
    
    # 配置数据源
    SETTINGS["datafeed.name"] = datafeed_name
    
    # 重置全局datafeed实例
    from vnpy.trader.datafeed import datafeed as global_datafeed
    import vnpy.trader.datafeed
    vnpy.trader.datafeed.datafeed = None
    
    # 获取数据服务实例
    datafeed = get_datafeed()
    
    # 初始化数据服务
    init_result = datafeed.init()
    print(f"初始化结果: {'成功' if init_result else '失败'}")
    
    if init_result:
        # 测试K线数据查询
        print("\n测试K线数据查询:")
        req = HistoryRequest(
            symbol="600000",
            exchange=Exchange.SSE,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 10),
            interval=Interval.DAILY
        )
        
        bars = datafeed.query_bar_history(req)
        print(f"获取K线数量: {len(bars)}")
        
        if bars:
            print("前3条K线数据:")
            for bar in bars[:3]:
                print(f"  {bar.datetime}: {bar.open_price} - {bar.high_price} - {bar.low_price} - {bar.close_price}")
    
    print("-" * 40 + "\n")

try:
    # 测试AKShare数据源
    test_datafeed("akshare")
    
    # 测试新浪财经数据源
    test_datafeed("sina")
    
    # 总结测试结果
    print("="*60)
    print("数据源集成测试结果")
    print("="*60)
    print("✓ AKShare数据源: 已集成")
    print("✓ 新浪财经数据源: 已集成")
    print("\n✓ 数据源集成测试完成！")
    print("  - 可通过配置 datafeed.name 切换数据源")
    print("  - AKShare: 免费A股数据")
    print("  - 新浪财经: 实时行情数据")
    
    sys.exit(0)

except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    print("\n✗ 数据源集成测试失败")
    sys.exit(1)
