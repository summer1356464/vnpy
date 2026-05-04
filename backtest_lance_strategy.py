#!/usr/bin/env python3
"""
Lance Breitstein策略回测脚本
"""
from datetime import datetime
import os
import sys

from vnpy.trader.constant import Interval
from vnpy.trader.setting import SETTINGS
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.strategy.strategies.lance_breitstein_strategy import LanceBreitsteinStrategy

from get_hs300_constituents import get_hs300_constituents


# 设置使用tx数据源和缓存
SETTINGS["datafeed.name"] = "tx"
SETTINGS["datafeed.use_cache"] = True


def main():
    """主函数"""
    # 获取沪深300成分股列表
    hs300_stocks = get_hs300_constituents()
    print(f"沪深300成分股数量: {len(hs300_stocks)}")
    
    # 创建AlphaLab实例
    lab_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alpha_lab")
    lab = AlphaLab(lab_path)
    
    # 初始化合约设置
    contract_settings = {}
    for vt_symbol in hs300_stocks:
        contract_settings[vt_symbol] = {
            "long_rate": 0.0002,
            "short_rate": 0.0002,
            "size": 1.0,
            "pricetick": 0.01
        }
    
    # 保存合约设置到JSON文件
    import json
    contract_json_path = os.path.join(lab_path, "contract.json")
    with open(contract_json_path, "w") as f:
        json.dump(contract_settings, f, indent=2)
    
    # 创建回测引擎
    engine = BacktestingEngine(lab)
    
    # 设置回测参数
    vt_symbols = hs300_stocks[:20]  # 使用已经下载数据的前20只股票进行回测
    interval = Interval.DAILY
    # 调整回测时间为2024-2025年
    start = datetime(2024, 1, 1)
    end = datetime(2025, 12, 31)
    capital = 1000000  # 初始资金100万
    
    engine.set_parameters(
        vt_symbols=vt_symbols,
        interval=interval,
        start=start,
        end=end,
        capital=capital
    )
    
    # 添加策略
    strategy_setting = {
        "lookback_days": 120,
        "vwap_days": 20,
        "short_ma": 10,
        "medium_ma": 30,
        "long_ma": 60,
        "trendline_points": 2,
        "position_size": 0.1
    }
    
    # 创建空的信号DataFrame
    import polars as pl
    signal_df = pl.DataFrame({
        "datetime": [],
        "symbol": [],
        "signal": []
    })
    
    engine.add_strategy(LanceBreitsteinStrategy, strategy_setting, signal_df)
    
    # 加载数据
    engine.load_data()
    
    # 运行回测
    engine.run_backtesting()
    
    # 计算结果
    daily_df = engine.calculate_result()
    if daily_df is not None:
        print("\n回测结果：")
        print(daily_df.tail())
        
        # 计算统计指标
        stats = engine.calculate_statistics()
        print("\n策略统计指标：")
        for key, value in stats.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
