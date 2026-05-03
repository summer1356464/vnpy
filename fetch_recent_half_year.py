#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拉取最近半年A股行情数据
使用TX数据源和Parquet缓存系统
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import akshare as ak

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.setting import SETTINGS


async def setup_datafeed():
    """设置TX数据源和缓存"""
    print("=" * 80)
    print("设置TX数据源和缓存")
    print("=" * 80)
    
    # 设置数据源配置
    SETTINGS["datafeed.name"] = "tx"  # 使用TX数据源
    SETTINGS["datafeed.use_cache"] = True  # 启用缓存
    SETTINGS["database.path"] = "database.db"  # 数据库路径
    
    print(f"数据源名称: {SETTINGS.get('datafeed.name')}")
    print(f"是否启用缓存: {SETTINGS.get('datafeed.use_cache')}")
    print(f"数据库路径: {SETTINGS.get('database.path')}")
    
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
        return datafeed
    else:
        print("✗ TX数据源初始化失败")
        sys.exit(1)


async def get_a_stock_list():
    """获取A股股票列表"""
    print("\n" + "=" * 80)
    print("获取A股股票列表")
    print("=" * 80)
    
    try:
        # 使用akshare获取A股股票列表
        stock_df = ak.stock_info_a_code_name()
        print(f"✓ 成功获取 {len(stock_df)} 只A股股票")
        
        # 处理所有A股股票
        print(f"将处理所有 {len(stock_df)} 只A股股票")
        
        return stock_df
    except Exception as e:
        print(f"✗ 获取A股股票列表失败: {e}")
        # 如果akshare失败，使用硬编码的股票列表作为备选
        fallback_stocks = [
            {"code": "000001", "name": "平安银行"},
            {"code": "000002", "name": "万科A"},
            {"code": "000858", "name": "五粮液"},
            {"code": "600000", "name": "浦发银行"},
            {"code": "600036", "name": "招商银行"},
            {"code": "600519", "name": "贵州茅台"},
            {"code": "601318", "name": "中国平安"},
            {"code": "601398", "name": "工商银行"},
            {"code": "601857", "name": "中国石油"},
            {"code": "601988", "name": "中国银行"}
        ]
        print(f"使用备选股票列表，共 {len(fallback_stocks)} 只股票")
        return pd.DataFrame(fallback_stocks)


async def fetch_stock_data(datafeed, symbol, name, start_date, end_date):
    """拉取单只股票的历史数据"""
    try:
        # 跳过北交所股票（920开头），TX数据源不支持
        if symbol.startswith("920"):
            print(f"\n{symbol} - {name}:")
            print(f"  ✗ 跳过北交所股票，TX数据源不支持")
            return False
            
        # 确定交易所
        if symbol.startswith("6"):
            exchange = Exchange.SSE
        else:
            exchange = Exchange.SZSE
        
        # 创建查询请求
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=Interval.DAILY,
            start=start_date,
            end=end_date
        )
        
        print(f"\n{symbol} - {name}:")
        print(f"  交易所: {exchange.value}")
        print(f"  时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        
        # 查询数据
        bars = datafeed.query_bar_history(req)
        
        if bars:
            print(f"  ✓ 成功获取 {len(bars)} 条K线数据")
            print(f"  第一条数据: {bars[0].datetime.strftime('%Y-%m-%d')}, 收盘价: {bars[0].close_price}")
            print(f"  最后一条数据: {bars[-1].datetime.strftime('%Y-%m-%d')}, 收盘价: {bars[-1].close_price}")
            
            # 等待异步缓存完成
            if hasattr(datafeed, "wait_cache_tasks_complete"):
                await datafeed.wait_cache_tasks_complete(timeout=10.0)
                print(f"  ✓ 数据已缓存到Parquet文件")
            
            return True
        else:
            print(f"  ✗ 未获取到数据")
            return False
            
    except IndexError as e:
        # 处理TX数据源不支持的股票导致的索引错误
        print(f"\n{symbol} - {name}:")
        print(f"  ✗ TX数据源不支持此股票: IndexError - {e}")
        return False
    except Exception as e:
        print(f"\n{symbol} - {name}:")
        print(f"  ✗ 获取数据失败: {type(e).__name__} - {e}")
        return False


async def main():
    """主函数"""
    print("=" * 80)
    print("拉取最近半年A股行情数据")
    print("=" * 80)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 计算最近半年的时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # 约6个月
        
        print(f"时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        
        # 1. 设置数据源
        datafeed = await setup_datafeed()
        
        # 2. 获取A股股票列表
        stock_df = await get_a_stock_list()
        
        # 3. 遍历股票列表，拉取数据
        print("\n" + "=" * 80)
        print("开始拉取股票数据")
        print("=" * 80)
        
        success_count = 0
        fail_count = 0
        
        for index, row in stock_df.iterrows():
            symbol = row["code"]
            name = row["name"]
            
            success = await fetch_stock_data(datafeed, symbol, name, start_date, end_date)
            
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            # 每处理10只股票显示进度
            if (index + 1) % 10 == 0:
                print(f"\n进度: 已处理 {index + 1}/{len(stock_df)} 只股票")
                print(f"成功: {success_count}, 失败: {fail_count}")
        
        # 4. 检查缓存文件
        print("\n" + "=" * 80)
        print("检查缓存文件")
        print("=" * 80)
        
        cache_root = "./data_cache"
        if os.path.exists(cache_root):
            print(f"✓ 缓存根目录: {cache_root} 存在")
            
            # 统计缓存文件数量
            import glob
            cache_files = glob.glob(f"{cache_root}/**/*.parquet", recursive=True)
            print(f"✓ 共生成 {len(cache_files)} 个Parquet缓存文件")
            
            # 显示部分缓存文件
            if cache_files:
                print("\n部分缓存文件:")
                for f in sorted(cache_files)[:5]:
                    size = os.path.getsize(f) / 1024
                    print(f"  - {os.path.basename(f)} ({size:.2f} KB)")
                if len(cache_files) > 5:
                    print(f"  ... 等 {len(cache_files)} 个文件")
        else:
            print(f"✗ 缓存根目录: {cache_root} 不存在")
        
        # 5. 输出统计结果
        print("\n" + "=" * 80)
        print("拉取完成")
        print("=" * 80)
        print(f"总股票数: {len(stock_df)}")
        print(f"成功拉取: {success_count} 只")
        print(f"失败拉取: {fail_count} 只")
        print(f"成功率: {success_count/len(stock_df)*100:.1f}%")
        print(f"时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        print("\n✓ 拉取任务完成！")
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("拉取失败")
        print("=" * 80)
        print(f"错误信息: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())