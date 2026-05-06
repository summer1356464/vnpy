#!/usr/bin/env python3
"""
检查缓存中的实际数据范围
"""
from datetime import datetime
import os
import sys
import pandas as pd
from pathlib import Path

# 设置缓存路径
CACHE_PATH = Path("/Users/bytedance/src/vnpy/data_cache")

# 检查标的的缓存数据范围
def check_cache_range(vt_symbol):
    print(f"\n检查 {vt_symbol} 的缓存数据范围...")
    
    # 解析标的信息
    if ".SSE" in vt_symbol:
        symbol, exchange = vt_symbol.split(".SSE")
        exchange = "SSE"
    elif ".SZSE" in vt_symbol:
        symbol, exchange = vt_symbol.split(".SZSE")
        exchange = "SZSE"
    else:
        print(f"不支持的标的格式: {vt_symbol}")
        return
    
    # 构建缓存目录路径
    symbol_dir = CACHE_PATH / f"{symbol}_{exchange}"
    bar_dir = symbol_dir / "bar" / "d"
    
    if not bar_dir.exists():
        print(f"没有找到 {vt_symbol} 的缓存目录")
        return
    
    # 获取所有parquet文件
    parquet_files = list(bar_dir.glob("*.parquet"))
    if not parquet_files:
        print(f"没有找到 {vt_symbol} 的缓存文件")
        return
    
    # 读取所有文件并合并
    all_dfs = []
    for file in parquet_files:
        df = pd.read_parquet(file)
        all_dfs.append(df)
    
    if not all_dfs:
        print(f"缓存文件为空")
        return
    
    combined_df = pd.concat(all_dfs)
    combined_df.sort_values(by="datetime", inplace=True)
    
    # 获取数据范围
    min_datetime = combined_df["datetime"].min()
    max_datetime = combined_df["datetime"].max()
    total_rows = len(combined_df)
    
    print(f"缓存数据范围: {min_datetime} 到 {max_datetime}")
    print(f"总数据条数: {total_rows}")

if __name__ == "__main__":
    # 检查几个标的的缓存范围
    check_cache_range("600000.SSE")
    check_cache_range("000001.SZSE")
