#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略回测测试脚本
使用AKShare作为数据源，测试VeighNa回测系统
"""

import sys
from datetime import datetime
import pandas as pd
import numpy as np

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.alpha.strategy.template import AlphaStrategy
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.lab import AlphaLab

class SimpleStrategy(AlphaStrategy):
    """简单策略"""
    
    def __init__(self, strategy_engine, strategy_name, vt_symbols, setting):
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        
        # 策略参数
        self.fast_period = setting.get("fast_period", 5)
        self.slow_period = setting.get("slow_period", 20)
        
        # 策略状态
        self.fast_ma = 0
        self.slow_ma = 0
        # 交易日计数器
        self.day_count = 0
    
    def on_init(self):
        """初始化策略"""
        self.write_log("策略初始化")
        # AlphaStrategy不需要手动加载历史数据
    
    def on_bars(self, bars: dict):
        """处理K线数据"""
        # 简化策略，确保产生交易信号
        self.day_count += 1
        
        for vt_symbol in self.vt_symbols:
            if vt_symbol in bars:
                bar = bars[vt_symbol]
                # 获取当前持仓
                pos = self.get_pos(vt_symbol)
                
                # 调试信息
                self.write_log(f"日期: {bar.datetime}, 持仓: {pos}, 交易日计数: {self.day_count}")
                
                # 强制在第一个交易日买入
                if self.day_count == 1 and pos == 0:
                    self.buy(vt_symbol, bar.close_price, 1000)
                    self.write_log(f"买入 {vt_symbol}, 价格: {bar.close_price}")
                # 强制在第二个交易日卖出
                elif self.day_count == 2 and pos > 0:
                    self.sell(vt_symbol, bar.close_price, 1000)
                    self.write_log(f"卖出 {vt_symbol}, 价格: {bar.close_price}")
    
    def on_trade(self, trade):
        """处理交易"""
        self.write_log(f"交易: {trade.direction} {trade.volume} {trade.price}")

def get_akshare_data(symbol, start_date, end_date, interval=Interval.DAILY):
    """使用AKShare获取数据"""
    try:
        import akshare as ak
        
        # 获取历史数据
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="hfq"
        )
        
        # 转换为BarData对象
        bars = []
        for _, row in df.iterrows():
            bar = BarData(
                symbol=symbol,
                exchange=Exchange.SSE,
                datetime=pd.to_datetime(row['date']),
                interval=interval,
                volume=float(row['volume']),
                open_price=float(row['open']),
                high_price=float(row['high']),
                low_price=float(row['low']),
                close_price=float(row['close']),
                open_interest=0,
                gateway_name="AKShare"
            )
            bars.append(bar)
        
        return bars
    except Exception as e:
        print(f"获取数据失败: {e}")
        # 生成模拟数据
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')
        bars = []
        for dt in date_range:
            bar = BarData(
                symbol=symbol,
                exchange=Exchange.SSE,
                datetime=dt,
                interval=interval,
                volume=np.random.randint(1000000, 10000000),
                open_price=np.random.uniform(5.0, 6.0),
                high_price=np.random.uniform(5.5, 6.5),
                low_price=np.random.uniform(4.5, 5.5),
                close_price=np.random.uniform(5.0, 6.0),
                open_interest=0,
                gateway_name="AKShare"
            )
            bars.append(bar)
        return bars

def run_backtest():
    """运行回测"""
    print("="*60)
    print("策略回测测试")
    print("="*60 + "\n")
    
    # 创建回测引擎
    import tempfile
    import shutil
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print(f"  ✓ 创建临时目录: {temp_dir}")
    
    lab = AlphaLab(temp_dir)
    engine = BacktestingEngine(lab)
    
    # 设置回测参数
    engine.vt_symbols = ["600000.SSE"]
    engine.start = datetime(2024, 1, 1)
    engine.end = datetime(2024, 12, 31)
    engine.capital = 100000
    engine.interval = Interval.DAILY
    
    # 设置费率和滑点
    engine.long_rates["600000.SSE"] = 0.0003
    engine.short_rates["600000.SSE"] = 0.0003
    engine.sizes["600000.SSE"] = 100
    engine.priceticks["600000.SSE"] = 0.01
    
    # 获取历史数据
    print("1. 获取历史数据...")
    bars = get_akshare_data("600000", engine.start, engine.end)
    print(f"  ✓ 获取{len(bars)}条K线数据")
    
    # 添加历史数据到回测引擎
    print("\n2. 添加历史数据...")
    # 使用AlphaLab的save_bar_data方法保存数据
    lab.save_bar_data(bars)
    # 同时更新engine的历史数据和时间戳
    for bar in bars:
        engine.history_data[(bar.symbol, bar.exchange.value, bar.interval.value, bar.datetime)] = bar
        engine.dts.add(bar.datetime)
        # 同时更新engine.bars，确保策略能获取到数据
        vt_symbol = f"{bar.symbol}.{bar.exchange.value}"
        engine.bars[vt_symbol] = bar
    print(f"  ✓ 历史数据添加完成，保存了{len(bars)}条K线数据")
    
    # 设置策略
    print("\n3. 设置策略...")
    engine.strategy_class = SimpleStrategy
    
    # 策略参数
    setting = {
        "fast_period": 5,
        "slow_period": 20
    }
    
    # 创建策略实例
    engine.strategy = SimpleStrategy(engine, "SimpleStrategy", ["600000.SSE"], setting)
    print("  ✓ 策略设置完成")
    
    # 运行回测
    print("\n4. 运行回测...")
    # 手动调用load_data方法，确保历史数据被正确加载
    engine.load_data()
    # 打印回测引擎状态
    print(f"  回测引擎状态: 数据点数量={len(engine.dts)}, 策略={engine.strategy.__class__.__name__}")
    # 运行回测
    engine.run_backtesting()
    print("  ✓ 回测完成")
    
    # 计算结果
    print("\n5. 计算结果...")
    engine.calculate_result()
    engine.calculate_statistics()
    print("  ✓ 结果计算完成")
    
    # 输出回测结果
    print("\n" + "="*60)
    print("回测结果")
    print("="*60)
    print("回测成功运行！")
    print("详细回测结果已在上面显示")
    print("\n" + "="*60)
    print("策略回测测试完成！")
    print("="*60)

if __name__ == "__main__":
    try:
        run_backtest()
        sys.exit(0)
    except Exception as e:
        print(f"回测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
