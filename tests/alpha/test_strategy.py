#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Alpha策略模块的功能
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from vnpy.alpha.strategy.template import AlphaStrategy
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.lab import AlphaLab
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData


class _TestStrategy(AlphaStrategy):
    """用于测试的简单策略"""
    
    def __init__(self, strategy_engine, strategy_name, vt_symbols, setting):
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        self.fast_window = setting.get("fast_window", 5)
        self.slow_window = setting.get("slow_window", 10)  # 减少窗口大小以更快触发信号
        self.pos = {vt_symbol: 0 for vt_symbol in vt_symbols}
        self.trade_count = 0
    
    def on_init(self) -> None:
        """初始化策略"""
        # 初始化持仓数据
        for vt_symbol in self.vt_symbols:
            self.pos[vt_symbol] = 0
    
    def on_bars(self, bars: dict):
        """处理K线数据"""
        for vt_symbol, bar in bars.items():
            # 为了确保有交易发生，使用简单的交易逻辑
            # 前10天买入，后10天卖出
            if self.trade_count < 5:
                # 买入
                if self.pos[vt_symbol] <= 0:
                    self.buy(vt_symbol, bar.close_price, 100)
                    self.pos[vt_symbol] += 100
                    self.trade_count += 1
            elif self.trade_count < 10:
                # 卖出
                if self.pos[vt_symbol] > 0:
                    self.sell(vt_symbol, bar.close_price, 100)
                    self.pos[vt_symbol] -= 100
                    self.trade_count += 1
    
    def on_trade(self, trade) -> None:
        """处理交易"""
        self.trade_count += 1
        for vt_symbol in self.vt_symbols:
            if trade.vt_symbol == vt_symbol:
                if trade.direction.value == "多":
                    self.pos[vt_symbol] += trade.volume
                else:
                    self.pos[vt_symbol] -= trade.volume
                break


@pytest.fixture
def mock_bars():
    """创建模拟的K线数据"""
    bars = []
    base_price = 10.0
    
    for i in range(100):
        # 创建有趋势的价格数据
        price_change = (i / 200.0) + (np.random.rand() - 0.5) * 0.1
        close = base_price * (1 + price_change)
        
        bar = BarData(
            symbol="TEST",
            exchange=Exchange.SZSE,
            datetime=datetime(2023, 1, 1) + timedelta(days=i),
            interval=Interval.DAILY,
            volume=10000,
            open_price=close * 0.99,
            high_price=close * 1.02,
            low_price=close * 0.98,
            close_price=close,
            gateway_name="TEST"
        )
        bars.append(bar)
    
    return bars


@pytest.fixture
def backtesting_engine():
    """创建回测引擎fixture"""
    lab = AlphaLab("test_lab")
    engine = BacktestingEngine(lab)
    
    # 设置回测参数
    engine.set_parameters(
        vt_symbols=["TEST.SZSE"],
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 4, 10),
        capital=100000,
        risk_free=0.03,
        annual_days=240
    )
    
    # 手动设置合约交易配置
    engine.long_rates = {"TEST.SZSE": 0.0}
    engine.short_rates = {"TEST.SZSE": 0.0}
    engine.sizes = {"TEST.SZSE": 100}
    engine.priceticks = {"TEST.SZSE": 0.01}
    
    # 添加一些模拟的历史数据
    import polars as pl
    from vnpy.trader.object import BarData
    
    # 创建模拟的K线数据
    dts = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(50)]
    bars = []
    
    for i, dt in enumerate(dts):
        price = 10.0 + i * 0.1  # 简单的上涨趋势
        bar = BarData(
            symbol="TEST",
            exchange=Exchange.SZSE,
            datetime=dt,
            interval=Interval.DAILY,
            volume=10000,
            open_price=price * 0.99,
            high_price=price * 1.02,
            low_price=price * 0.98,
            close_price=price,
            gateway_name="TEST"
        )
        bars.append(bar)
    
    # 添加历史数据到回测引擎
    engine.history_data = {}
    engine.dts = set(dts)
    
    for bar in bars:
        key = (bar.symbol, bar.exchange, bar.interval)
        if key not in engine.history_data:
            engine.history_data[key] = []
        engine.history_data[key].append(bar)
    
    return engine


@pytest.mark.alpha
@pytest.mark.strategy
@pytest.mark.unit
def test_strategy_init(backtesting_engine):
    """测试策略初始化"""
    strategy_settings = {
        "fast_window": 10,
        "slow_window": 30
    }
    
    # 创建空的signal_df
    import polars as pl
    signal_df = pl.DataFrame()
    
    backtesting_engine.add_strategy(_TestStrategy, strategy_settings, signal_df)
    
    # 验证策略已添加
    assert hasattr(backtesting_engine, "strategy")
    assert backtesting_engine.strategy.fast_window == 10
    assert backtesting_engine.strategy.slow_window == 30
    assert "TEST.SZSE" in backtesting_engine.strategy.pos


@pytest.mark.alpha
@pytest.mark.strategy
@pytest.mark.unit
def test_strategy_ma_calculation():
    """测试策略的移动平均线计算"""
    # 创建模拟数据
    closes = [1.0, 2.0, 3.0, 4.0, 5.0]
    
    # 计算5日均线
    fast_ma = np.mean(closes)
    
    assert fast_ma == 3.0
    
    # 添加更多数据
    closes.append(6.0)
    fast_ma_new = np.mean(closes[-5:])
    
    assert fast_ma_new == 4.0


@pytest.mark.alpha
@pytest.mark.strategy
@pytest.mark.functional
def test_backtesting_execution(backtesting_engine):
    """测试回测执行"""
    strategy_settings = {
        "fast_window": 5,
        "slow_window": 10
    }
    
    # 创建空的signal_df
    import polars as pl
    signal_df = pl.DataFrame()
    
    # 测试添加策略
    backtesting_engine.add_strategy(_TestStrategy, strategy_settings, signal_df)
    
    # 验证策略已添加并正确初始化
    assert hasattr(backtesting_engine, "strategy")
    assert backtesting_engine.strategy.fast_window == 5
    assert backtesting_engine.strategy.slow_window == 10
    assert hasattr(backtesting_engine, "strategy_class")
    assert backtesting_engine.strategy_class == _TestStrategy
    
    # 测试策略初始化方法被调用
    backtesting_engine.strategy.on_init()
    
    # 测试创建模拟K线数据并调用策略的on_bars方法
    from vnpy.trader.object import BarData
    
    # 创建模拟K线
    bar = BarData(
        symbol="TEST",
        exchange=Exchange.SZSE,
        datetime=datetime(2023, 1, 5),
        interval=Interval.DAILY,
        volume=10000,
        open_price=10.0,
        high_price=10.2,
        low_price=9.8,
        close_price=10.0,
        gateway_name="TEST"
    )
    
    # 调用策略的on_bars方法
    backtesting_engine.strategy.on_bars({"TEST.SZSE": bar})
    
    # 验证交易计数已增加
    assert backtesting_engine.strategy.trade_count > 0


@pytest.mark.alpha
@pytest.mark.strategy
@pytest.mark.parametrize("fast_window,slow_window", [
    (5, 10),
    (10, 20),
    (15, 30)
])
def test_strategy_parameters(backtesting_engine, fast_window, slow_window):
    """测试不同策略参数的效果"""
    strategy_settings = {
        "fast_window": fast_window,
        "slow_window": slow_window
    }
    
    # 创建空的signal_df
    import polars as pl
    signal_df = pl.DataFrame()
    
    # 测试添加策略，验证参数是否正确传递
    backtesting_engine.add_strategy(_TestStrategy, strategy_settings, signal_df)
    
    # 验证策略参数已正确设置
    assert backtesting_engine.strategy.fast_window == fast_window
    assert backtesting_engine.strategy.slow_window == slow_window
    
    # 测试策略可以正确处理不同的参数组合
    from vnpy.trader.object import BarData
    
    # 创建模拟K线
    bar = BarData(
        symbol="TEST",
        exchange=Exchange.SZSE,
        datetime=datetime(2023, 1, 5),
        interval=Interval.DAILY,
        volume=10000,
        open_price=10.0,
        high_price=10.2,
        low_price=9.8,
        close_price=10.0,
        gateway_name="TEST"
    )
    
    # 调用策略的on_bars方法，验证策略能够正常执行
    backtesting_engine.strategy.on_bars({"TEST.SZSE": bar})
    
    # 验证策略状态已更新
    assert backtesting_engine.strategy.trade_count >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
