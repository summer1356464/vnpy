#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用真实行情数据回测EquityDemoStrategy策略
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.trader.utility import round_to

from vnpy.alpha import AlphaLab, AlphaStrategy
from vnpy.alpha.strategy.strategies.equity_demo_strategy import EquityDemoStrategy
from vnpy.alpha.strategy.backtesting import BacktestingEngine


def run_backtest():
    """运行回测"""
    print("=" * 60)
    print("使用真实行情数据回测EquityDemoStrategy")
    print("=" * 60 + "\n")
    
    try:
        # 1. 初始化AlphaLab
        lab_path = Path(__file__).parent / "alpha_lab"
        lab = AlphaLab(str(lab_path))
        print(f"✓ AlphaLab初始化成功，数据存储路径: {lab_path}")
        
        # 2. 设置回测参数
        vt_symbols = ["600000.SSE", "600004.SSE"]  # 只有这两只股票有下载到的数据
        start_date = datetime.now() - timedelta(days=2 * 365)  # 最近2年
        end_date = datetime.now() - timedelta(days=1)  # 昨天
        interval = Interval.DAILY
        initial_capital = 1000000  # 初始资金100万
        
        print(f"✓ 回测参数设置完成")
        print(f"  - 股票代码: {vt_symbols}")
        print(f"  - 时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        print(f"  - 初始资金: {initial_capital}")
        
        # 3. 检查数据是否存在
        print(f"\n3. 检查历史数据...")
        data_exist = True
        for vt_symbol in vt_symbols:
            if interval == Interval.DAILY:
                file_path = lab_path.joinpath("daily", f"{vt_symbol}.parquet")
            else:
                file_path = lab_path.joinpath("minute", f"{vt_symbol}.parquet")
            
            if not file_path.exists():
                print(f"  ✗ 数据文件不存在: {file_path}")
                data_exist = False
            else:
                print(f"  ✓ 数据文件存在: {file_path}")
        
        if not data_exist:
            print("\n请先运行download_real_data.py下载数据！")
            return False
        
        # 4. 创建回测引擎
        engine = BacktestingEngine(lab)
        print(f"✓ 回测引擎创建完成")
        
        # 5. 设置合约信息
        print(f"\n5. 设置合约信息...")
        for vt_symbol in vt_symbols:
            lab.add_contract_setting(
                vt_symbol=vt_symbol,
                long_rate=0.0003,
                short_rate=0.0003,
                size=100,
                pricetick=0.01
            )
            print(f"  ✓ 设置合约: {vt_symbol}")
        
        # 6. 设置回测参数
        print(f"\n6. 设置回测参数...")
        engine.set_parameters(
            vt_symbols=vt_symbols,
            interval=interval,
            start=start_date,
            end=end_date,
            capital=initial_capital,
            annual_days=240
        )
        print(f"  ✓ 回测参数设置完成")
        
        # 6. 生成模拟信号数据
        print(f"\n6. 生成模拟信号数据...")
        
        # 加载历史数据用于生成信号
        all_bars = {}
        for vt_symbol in vt_symbols:
            bars = lab.load_bar_data(vt_symbol, interval, start_date, end_date)
            all_bars[vt_symbol] = bars
        
        # 生成信号数据
        import polars as pl
        import numpy as np
        
        signal_data = []
        
        # 获取所有唯一的日期
        all_dates = set()
        for vt_symbol, bars in all_bars.items():
            for bar in bars:
                all_dates.add(bar.datetime)
        
        # 按日期排序
        sorted_dates = sorted(all_dates)
        
        for dt in sorted_dates:
            for vt_symbol in vt_symbols:
                # 简单的模拟信号策略：基于前N天的收益率
                signal = 0.0
                bars = all_bars[vt_symbol]
                
                # 找到当前日期的bar
                current_idx = -1
                for i, bar in enumerate(bars):
                    if bar.datetime == dt:
                        current_idx = i
                        break
                
                if current_idx >= 5:  # 至少需要5天数据
                    # 计算前5天的收益率
                    prev_close = bars[current_idx - 5].close_price
                    current_close = bars[current_idx].close_price
                    return_5d = (current_close - prev_close) / prev_close
                    
                    # 生成信号
                    signal = return_5d * 100  # 放大信号值
                
                signal_data.append({
                    "datetime": dt,
                    "vt_symbol": vt_symbol,
                    "signal": signal
                })
        
        # 创建信号DataFrame
        signal_df = pl.DataFrame(signal_data)
        
        print(f"  ✓ 模拟信号数据生成完成，共 {len(signal_df)} 条记录")
        
        # 7. 添加策略
        print(f"\n7. 添加策略...")
        strategy_setting = {
            "top_k": 2,         # 持有最多2只股票
            "n_drop": 1,        # 每次卖出1只股票
            "min_days": 2,      # 最小持仓2天
            "cash_ratio": 0.8,  # 现金利用率80%
            "price_add": 0.01   # 降低订单价格调整比例，使订单更容易成交
        }
        
        engine.add_strategy(EquityDemoStrategy, strategy_setting, signal_df)
        print(f"  ✓ 策略添加完成: EquityDemoStrategy")
        print(f"  ✓ 策略参数: {strategy_setting}")
        
        # 8. 加载历史数据
        print(f"\n8. 加载历史数据...")
        engine.load_data()
        print(f"  ✓ 历史数据加载完成")
        
        # 9. 开始回测
        print(f"\n9. 开始回测...")
        engine.run_backtesting()
        
        # 10. 计算结果
        print(f"\n10. 计算回测结果...")
        result_df = engine.calculate_result()
        
        if result_df is None:
            print("  ✗ 回测结果计算失败")
            return False
        
        print(f"  ✓ 回测结果计算完成，共 {len(result_df)} 个交易日")
        
        # 11. 统计分析
        print(f"\n11. 统计分析...")
        statistics = engine.calculate_statistics()
        
        # 打印统计结果
        print("\n" + "=" * 60)
        print("回测统计结果")
        print("=" * 60)
        print(f"起始资金: {statistics['capital']:,.2f}")
        print(f"结束资金: {statistics['end_balance']:,.2f}")
        print(f"总收益率: {statistics['total_return']:,.2f}%")
        print(f"年化收益: {statistics['annual_return']:,.2f}%")
        print(f"最大回撤: {statistics['max_ddpercent']:,.2f}%")
        print(f"夏普比率: {statistics['sharpe_ratio']:,.2f}")
        print(f"总成交笔数: {statistics['total_trade_count']}")
        print(f"日均成交笔数: {statistics['daily_trade_count']:.2f}")
        print("=" * 60)
        
        # 11. 保存结果
        print(f"\n11. 保存回测结果...")
        result_path = Path("/Users/bumblebee/workspace/finance/vnpy/backtest_results")
        result_path.mkdir(parents=True, exist_ok=True)
        
        # 保存详细结果
        result_file = result_path.joinpath(f"equity_demo_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet")
        result_df.write_parquet(result_file)
        print(f"  ✓ 回测结果保存成功: {result_file}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 回测失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 运行回测
    success = run_backtest()
    
    if success:
        print("\n回测完成！")
        sys.exit(0)
    else:
        print("\n回测失败，请检查配置和数据")
        sys.exit(1)
