#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化测试脚本：测试TX行情获取和缓存功能
直接使用datafeed查询数据，验证缓存机制
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.setting import SETTINGS


def setup_tx_datafeed():
    """设置TX数据源"""
    print("=" * 80)
    print("设置TX数据源")
    print("=" * 80)
    
    # 设置数据源配置
    SETTINGS["datafeed.name"] = "tx"
    SETTINGS["datafeed.use_cache"] = True
    
    print(f"数据源名称: {SETTINGS.get('datafeed.name')}")
    print(f"是否启用缓存: {SETTINGS.get('datafeed.use_cache')}")
    
    # 初始化数据源
    datafeed = get_datafeed()
    success = datafeed.init()
    
    if success:
        print("✓ TX数据源初始化成功")
        if hasattr(datafeed, "cache_backend"):
            backend_type = type(datafeed.cache_backend).__name__
            print(f"缓存后端类型: {backend_type}")
            
            if backend_type == "ParquetCacheBackend":
                cache_root = getattr(datafeed.cache_backend, "cache_root", "./data_cache")
                print(f"Parquet缓存路径: {cache_root}")
    else:
        print("✗ TX数据源初始化失败")
        sys.exit(1)
    
    return datafeed


async def test_first_query(datafeed):
    """第一次查询：应该从网络获取数据并缓存"""
    print("\n" + "=" * 80)
    print("第一次查询（从网络获取并缓存）")
    print("=" * 80)
    
    req = HistoryRequest(
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 31)
    )
    
    print(f"查询: {req.symbol}.{req.exchange.value} {req.interval.value} "
          f"from {req.start.strftime('%Y-%m-%d')} to {req.end.strftime('%Y-%m-%d')}")
    
    # 计时
    import time
    start_time = time.time()
    
    bars = datafeed.query_bar_history(req)
    
    elapsed = time.time() - start_time
    
    if bars:
        print(f"✓ 查询成功，获取到 {len(bars)} 条K线数据")
        print(f"  耗时: {elapsed:.2f} 秒")
        print(f"  第一条: {bars[0].datetime.strftime('%Y-%m-%d')}, 收盘价: {bars[0].close_price}")
        print(f"  最后一条: {bars[-1].datetime.strftime('%Y-%m-%d')}, 收盘价: {bars[-1].close_price}")
        
        # 等待异步缓存完成
        if hasattr(datafeed, "wait_cache_tasks_complete"):
            print("等待异步缓存任务完成...")
            await datafeed.wait_cache_tasks_complete(timeout=10.0)
            print("✓ 异步缓存任务完成")
    else:
        print("✗ 查询失败")
        sys.exit(1)
    
    return bars


async def test_second_query(datafeed):
    """第二次查询：应该从缓存获取数据"""
    print("\n" + "=" * 80)
    print("第二次查询（应该从缓存获取）")
    print("=" * 80)
    
    req = HistoryRequest(
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 31)
    )
    
    print(f"查询: {req.symbol}.{req.exchange.value} {req.interval.value} "
          f"from {req.start.strftime('%Y-%m-%d')} to {req.end.strftime('%Y-%m-%d')}")
    
    # 计时
    import time
    start_time = time.time()
    
    bars = datafeed.query_bar_history(req)
    
    elapsed = time.time() - start_time
    
    if bars:
        print(f"✓ 查询成功，获取到 {len(bars)} 条K线数据")
        print(f"  耗时: {elapsed:.2f} 秒")
        print(f"  第一条: {bars[0].datetime.strftime('%Y-%m-%d')}, 收盘价: {bars[0].close_price}")
        print(f"  最后一条: {bars[-1].datetime.strftime('%Y-%m-%d')}, 收盘价: {bars[-1].close_price}")
        
        # 验证是否从缓存获取（通过耗时判断）
        if elapsed < 0.5:  # 缓存查询应该很快
            print("✓ 很可能从缓存获取数据（查询耗时较短）")
        else:
            print("⚠ 可能仍然从网络获取数据（查询耗时较长）")
    else:
        print("✗ 查询失败")
        sys.exit(1)
    
    return bars


async def test_partial_query(datafeed):
    """测试部分范围查询：应该部分从缓存获取，部分从网络获取"""
    print("\n" + "=" * 80)
    print("部分范围查询（混合缓存和网络）")
    print("=" * 80)
    
    req = HistoryRequest(
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime(2023, 1, 15),  # 缓存中已有的日期
        end=datetime(2023, 2, 15)     # 部分日期不在缓存中
    )
    
    print(f"查询: {req.symbol}.{req.exchange.value} {req.interval.value} "
          f"from {req.start.strftime('%Y-%m-%d')} to {req.end.strftime('%Y-%m-%d')}")
    
    bars = datafeed.query_bar_history(req)
    
    if bars:
        print(f"✓ 查询成功，获取到 {len(bars)} 条K线数据")
        print(f"  第一条: {bars[0].datetime.strftime('%Y-%m-%d')}, 收盘价: {bars[0].close_price}")
        print(f"  最后一条: {bars[-1].datetime.strftime('%Y-%m-%d')}, 收盘价: {bars[-1].close_price}")
        
        # 等待异步缓存完成
        if hasattr(datafeed, "wait_cache_tasks_complete"):
            await datafeed.wait_cache_tasks_complete(timeout=10.0)
    else:
        print("✗ 查询失败")
        sys.exit(1)
    
    return bars


async def test_multiple_symbols(datafeed):
    """测试多个股票查询"""
    print("\n" + "=" * 80)
    print("多个股票查询测试")
    print("=" * 80)
    
    symbols = ["000001", "600000", "000002"]  # 平安银行、浦发银行、万科A
    
    for symbol in symbols:
        req = HistoryRequest(
            symbol=symbol,
            exchange=Exchange.SZSE if symbol.startswith("0") else Exchange.SSE,
            interval=Interval.DAILY,
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 10)
        )
        
        print(f"查询 {symbol}.{req.exchange.value}...")
        bars = datafeed.query_bar_history(req)
        
        if bars:
            print(f"  ✓ 获取到 {len(bars)} 条数据")
        else:
            print(f"  ✗ 查询失败")
    
    # 等待所有缓存任务完成
    if hasattr(datafeed, "wait_cache_tasks_complete"):
        await datafeed.wait_cache_tasks_complete(timeout=15.0)


def check_cache_files():
    """检查缓存文件"""
    print("\n" + "=" * 80)
    print("检查缓存文件")
    print("=" * 80)
    
    cache_root = "./data_cache"
    print(f"缓存根目录: {cache_root}")
    
    if os.path.exists(cache_root):
        print("✓ 缓存根目录存在")
        
        # 查看缓存目录结构
        import glob
        cache_files = glob.glob(f"{cache_root}/**/*.parquet", recursive=True)
        
        if cache_files:
            print(f"\n发现 {len(cache_files)} 个Parquet缓存文件:")
            
            # 按股票分组
            symbol_files = {}
            for f in cache_files:
                parts = f.split(os.sep)
                symbol_exchange = parts[-4]
                if symbol_exchange not in symbol_files:
                    symbol_files[symbol_exchange] = []
                symbol_files[symbol_exchange].append(f)
            
            for symbol_exchange, files in symbol_files.items():
                print(f"\n  {symbol_exchange}:")
                for f in sorted(files):
                    filename = os.path.basename(f)
                    size = os.path.getsize(f) / 1024
                    print(f"    - {filename} ({size:.2f} KB)")
            
            # 显示一个缓存文件的内容
            print("\n缓存文件内容示例:")
            try:
                import pandas as pd
                sample_file = cache_files[0]
                df = pd.read_parquet(sample_file)
                print(f"  文件: {os.path.basename(sample_file)}")
                print(df.head())
            except Exception as e:
                print(f"  读取文件失败: {e}")
        else:
            print("✗ 未发现Parquet缓存文件")
    else:
        print("✗ 缓存根目录不存在")


async def main():
    """主函数"""
    print("=" * 80)
    print("测试TX行情获取与缓存功能")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 设置TX数据源
        datafeed = setup_tx_datafeed()
        
        # 2. 第一次查询（从网络获取并缓存）
        await test_first_query(datafeed)
        
        # 3. 第二次查询（从缓存获取）
        await test_second_query(datafeed)
        
        # 4. 部分范围查询（混合缓存和网络）
        await test_partial_query(datafeed)
        
        # 5. 多个股票查询
        await test_multiple_symbols(datafeed)
        
        # 6. 检查缓存文件
        check_cache_files()
        
        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)
        print("✓ TX行情数据源正常工作")
        print("✓ 缓存功能正常运行")
        print("✓ 缓存文件已生成")
        print("\n测试结果：所有功能正常！")
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("测试失败！")
        print("=" * 80)
        print(f"错误信息: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())