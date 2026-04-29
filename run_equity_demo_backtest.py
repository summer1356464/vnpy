#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EquityDemoStrategy回测脚本
使用模拟数据测试多因子选股策略
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import polars as pl

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.alpha.strategy.strategies.equity_demo_strategy import EquityDemoStrategy
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.lab import AlphaLab

def generate_sample_bars(symbol: str, start: datetime, end: datetime, interval: Interval) -> list[BarData]:
    """生成模拟K线数据"""
    date_range = pd.date_range(start=start, end=end, freq='B')
    bars = []
    
    # 为每个股票设置不同的初始价格，避免价格过低
    base_prices = {
        "600000": 15.0,
        "600001": 20.0,
        "600002": 18.0,
        "600003": 25.0,
        "600004": 30.0
    }
    
    # 获取当前股票的初始价格
    base_price = base_prices.get(symbol, 15.0)
    
    for dt in date_range:
        # 生成随机波动的价格，但限制波动幅度，避免价格过低或过高
        change = np.random.uniform(-0.01, 0.01)
        base_price *= (1 + change)
        
        # 确保价格不会太低
        if base_price < 5.0:
            base_price = 5.0
        
        # 确保价格不会太高
        if base_price > 100.0:
            base_price = 100.0
        
        open_price = base_price
        high_price = base_price * (1 + np.random.uniform(0, 0.005))
        low_price = base_price * (1 - np.random.uniform(0, 0.005))
        close_price = base_price * (1 + np.random.uniform(-0.0025, 0.0025))
        
        bar = BarData(
            symbol=symbol,
            exchange=Exchange.SSE,
            datetime=dt,
            interval=interval,
            volume=float(np.random.randint(1000000, 10000000)),
            turnover=float(np.random.randint(10000000, 100000000)),
            open_price=round(open_price, 2),
            high_price=round(high_price, 2),
            low_price=round(low_price, 2),
            close_price=round(close_price, 2),
            open_interest=0,
            gateway_name="SIMULATION"
        )
        bars.append(bar)
    
    return bars

def generate_sample_signal(symbols: list[str], start: datetime, end: datetime) -> pl.DataFrame:
    """生成模拟信号数据"""
    date_range = pd.date_range(start=start, end=end, freq='B')
    
    # 生成确定性的信号数据，确保能产生交易
    data = []
    for i, dt in enumerate(date_range):
        for j, symbol in enumerate(symbols):
            # 生成有规律的信号值，确保不同股票有不同的信号强度
            # 前几个股票在奇数天有正信号，偶数天有负信号，后几个股票相反
            if j < len(symbols) // 2:
                signal = 1.0 if i % 2 == 0 else -1.0
            else:
                signal = -1.0 if i % 2 == 0 else 1.0
            
            # 添加一些随机波动
            signal += np.random.normal(0, 0.1)
            
            data.append({
                "datetime": dt,
                "vt_symbol": symbol,
                "signal": signal
            })
    
    # 转换为polars DataFrame
    signal_df = pl.DataFrame(data)
    return signal_df

def run_equity_demo_backtest():
    """运行EquityDemoStrategy回测"""
    print("="*60)
    print("EquityDemoStrategy回测")
    print("="*60 + "\n")
    
    # 创建临时目录存储数据
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    print(f"  ✓ 创建临时目录: {temp_dir}")
    
    try:
        # 创建AlphaLab和BacktestingEngine
        lab = AlphaLab(temp_dir)
        engine = BacktestingEngine(lab)
        
        # 设置回测参数
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        vt_symbols = ["600000.SSE", "600001.SSE", "600002.SSE", "600003.SSE", "600004.SSE"]
        
        print(f"\n1. 设置回测参数:")
        print(f"   起始日期: {start_date}")
        print(f"   结束日期: {end_date}")
        print(f"   测试标的: {vt_symbols}")
        
        # 设置合约信息
        for vt_symbol in vt_symbols:
            # 使用save_bar_data前，需要先设置合约信息
            lab.add_contract_setting(
                vt_symbol=vt_symbol,
                long_rate=0.0003,
                short_rate=0.0003,
                size=100,
                pricetick=0.01
            )
        
        engine.set_parameters(
            vt_symbols=vt_symbols,
            interval=Interval.DAILY,
            start=start_date,
            end=end_date,
            capital=1000000,
            annual_days=240
        )
        
        # 生成并保存历史数据
        print("\n2. 生成历史数据...")
        for vt_symbol in vt_symbols:
            symbol = vt_symbol.split(".")[0]
            bars = generate_sample_bars(symbol, start_date, end_date, Interval.DAILY)
            lab.save_bar_data(bars)
            print(f"   ✓ 生成{vt_symbol}的{len(bars)}条K线数据")
        
        # 生成信号数据
        print("\n3. 生成信号数据...")
        signal_df = generate_sample_signal(vt_symbols, start_date, end_date)
        print(f"   ✓ 生成{len(signal_df)}条信号数据")
        
        # 添加策略
        print("\n4. 设置策略...")
        strategy_setting = {
            "top_k": 3,         # 持有最多3只股票
            "n_drop": 1,        # 每次卖出1只股票
            "min_days": 2,      # 最小持仓2天
            "cash_ratio": 0.95, # 现金利用率95%
            "price_add": 0.01   # 降低订单价格调整比例，使订单更容易成交
        }
        
        engine.add_strategy(EquityDemoStrategy, strategy_setting, signal_df)
        print(f"   ✓ 策略参数: {strategy_setting}")
        
        # 加载数据
        print("\n5. 加载回测数据...")
        engine.load_data()
        print(f"   ✓ 数据加载完成")
        
        # 运行回测
        print("\n6. 运行回测...")
        engine.run_backtesting()
        print(f"   ✓ 回测完成")
        
        # 计算结果
        print("\n7. 计算回测结果...")
        daily_df = engine.calculate_result()
        statistics = engine.calculate_statistics()
        print(f"   ✓ 结果计算完成")
        
        # 输出统计结果
        print("\n" + "="*60)
        print("回测统计结果")
        print("="*60)
        print(f"起始资金: {statistics['capital']:,.2f}")
        print(f"结束资金: {statistics['end_balance']:,.2f}")
        print(f"总收益率: {statistics['total_return']:,.2f}%")
        print(f"年化收益: {statistics['annual_return']:,.2f}%")
        print(f"最大回撤: {statistics['max_ddpercent']:,.2f}%")
        print(f"夏普比率: {statistics['sharpe_ratio']:,.2f}")
        print(f"总成交笔数: {statistics['total_trade_count']}")
        print(f"日均成交笔数: {statistics['daily_trade_count']:.2f}")
        print("="*60)
        
        # 保存回测结果
        print("\n8. 保存回测结果...")
        result_dir = os.path.join(temp_dir, "backtest_results")
        os.makedirs(result_dir, exist_ok=True)
        
        # 保存每日结果
        daily_df.write_parquet(os.path.join(result_dir, "daily_results.parquet"))
        
        # 保存统计结果
        stats_df = pl.DataFrame([statistics])
        stats_df.write_parquet(os.path.join(result_dir, "statistics.parquet"))
        
        print(f"   ✓ 回测结果保存至: {result_dir}")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n  ✓ 清理临时目录: {temp_dir}")
    
    print("\n" + "="*60)
    print("EquityDemoStrategy回测完成！")
    print("="*60)

if __name__ == "__main__":
    try:
        run_equity_demo_backtest()
        sys.exit(0)
    except Exception as e:
        print(f"回测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)