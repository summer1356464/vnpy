#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载真实A股行情数据并保存为项目所需格式
基于免费数据源AKShare
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import akshare as ak
import polars as pl
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.utility import extract_vt_symbol
from vnpy.alpha import AlphaLab, logger


def download_data():
    """下载A股历史数据"""
    print("=" * 60)
    print("下载真实A股行情数据")
    print("=" * 60 + "\n")
    
    try:
        # 1. 初始化AlphaLab
        lab_path = Path(__file__).parent / "alpha_lab"
        lab = AlphaLab(str(lab_path))
        print(f"✓ AlphaLab初始化成功，数据存储路径: {lab_path}")
        
        # 2. 设置下载参数
        symbols = ["600000", "600001", "600002", "600003", "600004"]  # 示例股票代码
        exchange = Exchange.SSE  # 上海证券交易所
        interval = Interval.DAILY  # 日线数据
        
        # 设置时间范围（最近3年）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3 * 365)
        
        print(f"✓ 下载参数设置完成")
        print(f"  - 股票代码: {symbols}")
        print(f"  - 交易所: {exchange.value}")
        print(f"  - 时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        # 3. 下载数据
        for symbol in symbols:
            print(f"\n4. 下载股票 {symbol} 数据...")
            
            # 下载历史数据
            try:
                # 使用AKShare的腾讯财经接口获取A股历史数据
                # 转换symbol格式为腾讯财经所需的格式（sh600000或sz000001）
                if exchange == Exchange.SSE:
                    ak_symbol = f"sh{symbol}"
                else:
                    ak_symbol = f"sz{symbol}"
                    
                print(f"  使用腾讯财经接口获取 {ak_symbol} 数据...")
                df = ak.stock_zh_a_hist_tx(
                    symbol=ak_symbol,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust="hfq"
                )
                print(f"  ✓ 数据获取成功: {len(df)} 条记录")
                
                # 打印完整数据信息
                print(f"  ✓ 数据字段: {list(df.columns)}")
                print(f"  ✓ 数据前3行:")
                print(df.head(3))
                
                # 字段映射（处理中文和英文字段名）
                field_mapping = {
                    'date': 'date',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'amount': 'turnover'  # 腾讯财经接口返回的是amount字段
                }
                
                # 重命名列
                df = df.rename(columns=field_mapping)
                print(f"  ✓ 重命名后字段: {list(df.columns)}")
                
                # 确保数据包含必要的字段
                required_fields = ['date', 'open', 'high', 'low', 'close', 'turnover']
                for field in required_fields:
                    if field not in df.columns:
                        print(f"  ✗ 数据缺少{field}字段")
                        raise ValueError(f"Missing required field: {field}")
                
                # 根据成交额和收盘价计算成交量（成交量 = 成交额 / 收盘价 / 100，假设每手100股）
                df['volume'] = df['turnover'] / df['close'] / 100
                df['volume'] = df['volume'].round(0)  # 成交量取整
                print(f"  ✓ 计算成交量完成")
                
                # 添加open_interest字段（如果不存在）
                if 'open_interest' not in df.columns:
                    df['open_interest'] = 0
                    print(f"  ✓ 添加持仓量字段")
                    
                # 转换日期格式
                df['datetime'] = pd.to_datetime(df['date'])
                
                # 过滤时间范围
                df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]
                
                if df.empty:
                    print(f"  ✗ 时间范围内无数据")
                    continue
                
                print(f"  ✓ 过滤后数据: {len(df)} 条记录")
                
                # 保存为parquet格式
                vt_symbol = f"{symbol}.{exchange.value}"
                if interval == Interval.DAILY:
                    file_path = lab_path.joinpath("daily", f"{vt_symbol}.parquet")
                else:
                    file_path = lab_path.joinpath("minute", f"{vt_symbol}.parquet")
                
                # 确保目录存在
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 转换为polars DataFrame
                pl_df = pl.from_pandas(df)
                
                # 选择需要的列
                pl_df = pl_df.select([
                    "datetime",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "turnover",
                    "open_interest"
                ])
                
                # 保存为parquet文件
                pl_df.write_parquet(file_path)
                print(f"  ✓ 数据保存成功: {file_path}")
                
            except Exception as e:
                print(f"  ✗ 下载失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 5. 总结
        print("\n" + "=" * 60)
        print("数据下载完成")
        print("=" * 60)
        print("✓ 成功下载真实A股行情数据")
        print(f"✓ 数据存储在: {lab_path}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 导入pandas
    try:
        import pandas as pd
    except ImportError:
        print("安装pandas...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
        import pandas as pd
    
    # 安装或更新AKShare
    print("检查AKShare模块...")
    try:
        import akshare as ak
        print(f"当前AKShare版本: {ak.__version__}")
        print("更新AKShare到最新版本...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "akshare", "-U"])
        print("AKShare更新完成")
    except ImportError:
        print("安装AKShare...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "akshare"])
    
    # 下载数据
    success = download_data()
    
    if success:
        print("\n数据下载成功，可以开始使用真实数据进行回测了！")
        sys.exit(0)
    else:
        print("\n数据下载失败，请检查网络连接和配置")
        sys.exit(1)
