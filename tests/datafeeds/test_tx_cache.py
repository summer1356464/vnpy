#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试TX数据源、缓存系统和回测框架的完整流程
"""

import sys
import os
import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import asyncio

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.setting import SETTINGS
from vnpy.alpha.strategy.template import AlphaStrategy
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.lab import AlphaLab


class SimpleTxStrategy(AlphaStrategy):
    """简单的TX策略，用于测试行情获取和缓存功能"""
    
    def __init__(self, strategy_engine, strategy_name, vt_symbols, setting):
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        
        # 策略参数
        self.buy_day = setting.get("buy_day", 5)
        self.sell_day = setting.get("sell_day", 15)
        
        # 策略状态
        self.day_count = 0
        self.holding = False
        
        self.write_log(f"策略初始化：buy_day={self.buy_day}, sell_day={self.sell_day}")
    
    def on_init(self):
        """初始化策略"""
        self.write_log("策略初始化完成")
    
    def on_bars(self, bars: dict):
        """处理K线数据"""
        self.day_count += 1
        
        for vt_symbol in self.vt_symbols:
            if vt_symbol in bars:
                bar = bars[vt_symbol]
                # 获取当前持仓
                pos = self.get_pos(vt_symbol)
                
                # 策略逻辑：简单的买入卖出条件
                if self.day_count == self.buy_day and pos == 0:
                    # 买入
                    self.buy(vt_symbol, bar.close_price, 100)
                    self.holding = True
                elif self.day_count == self.sell_day and pos > 0:
                    # 卖出
                    self.sell(vt_symbol, bar.close_price, 100)
                    self.holding = False


@pytest.fixture(scope="module")
def setup_tx_datafeed():
    """设置TX数据源的fixture"""
    # 设置数据源配置
    SETTINGS["datafeed.name"] = "tx"  # 使用TX数据源
    SETTINGS["datafeed.use_cache"] = True  # 启用缓存
    
    # 初始化数据源
    datafeed = get_datafeed()
    success = datafeed.init()
    
    assert success, "TX数据源初始化失败"
    yield datafeed
    
    # 清理操作
    if hasattr(datafeed, "close"):
        datafeed.close()


@pytest.mark.asyncio
@pytest.mark.datafeed
@pytest.mark.tx
def test_tx_data_query(setup_tx_datafeed):
    """测试TX数据源的直接查询功能"""
    datafeed = setup_tx_datafeed
    
    # 创建查询请求
    req = HistoryRequest(
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 10)
    )
    
    # 查询数据
    bars = datafeed.query_bar_history(req)
    
    assert bars, "未获取到数据"
    assert len(bars) > 0, "获取到的数据为空"
    
    # 验证数据格式
    for bar in bars:
        assert isinstance(bar, BarData), "返回的数据不是BarData类型"
        assert bar.datetime is not None, "BarData缺少datetime字段"
        assert bar.close_price > 0, "收盘价应该大于0"
    
    # 等待异步缓存完成
    if hasattr(datafeed, "wait_cache_tasks_complete"):
        asyncio.run(datafeed.wait_cache_tasks_complete(timeout=10.0))


@pytest.mark.datafeed
@pytest.mark.tx
@pytest.mark.strategy
def test_tx_backtesting(setup_tx_datafeed):
    """测试TX数据源的回测功能"""
    # 创建投研实验室
    lab = AlphaLab("backtest_lab")
    
    # 创建回测引擎
    engine = BacktestingEngine(lab)
    
    # 设置回测参数
    engine.set_parameters(
        vt_symbols=["000001.SZ"],  # 平安银行
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 6, 30),
        capital=100000,  # 10万起始资金
        risk_free=0.03,  # 无风险利率
        annual_days=240  # 年交易日数
    )
    
    # 添加策略
    strategy_settings = {
        "buy_day": 10,  # 第10个交易日买入
        "sell_day": 50   # 第50个交易日卖出
    }
    engine.add_strategy(SimpleTxStrategy, strategy_settings)
    
    # 加载数据
    engine.load_data()
    
    # 运行回测
    engine.run_backtesting()
    
    # 计算结果
    daily_df = engine.calculate_result()
    
    # 验证结果
    assert daily_df is not None, "回测结果为空"
    assert not daily_df.empty, "回测结果DataFrame为空"
    
    # 计算统计指标
    statistics = engine.calculate_statistics()
    
    assert statistics is not None, "统计指标计算失败"
    assert isinstance(statistics, dict), "统计指标应该是字典类型"
    assert "total_return" in statistics, "统计指标缺少total_return"


@pytest.mark.datafeed
@pytest.mark.tx
@pytest.mark.cache
def test_tx_cache_files(setup_tx_datafeed):
    """测试TX数据源的缓存文件生成"""
    # 先执行数据查询，确保数据被缓存
    datafeed = setup_tx_datafeed
    
    req = HistoryRequest(
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 10)
    )
    
    bars = datafeed.query_bar_history(req)
    
    # 等待异步缓存完成
    if hasattr(datafeed, "wait_cache_tasks_complete"):
        asyncio.run(datafeed.wait_cache_tasks_complete(timeout=10.0))
    
    # 检查Parquet缓存文件
    cache_dir = "./data_cache/000001_SZSE/bar/d/"
    
    assert os.path.exists(cache_dir), f"缓存目录不存在: {cache_dir}"
    
    cache_files = os.listdir(cache_dir)
    assert len(cache_files) > 0, "缓存目录中没有文件"
    
    # 验证至少一个缓存文件可以正常读取
    sample_file = os.path.join(cache_dir, sorted(cache_files)[0])
    df = pd.read_parquet(sample_file)
    
    assert not df.empty, "缓存文件内容为空"
    assert "close" in df.columns, "缓存文件缺少close列"


@pytest.mark.integration
@pytest.mark.datafeed
@pytest.mark.tx
@pytest.mark.slow
def test_tx_complete_flow(setup_tx_datafeed):
    """测试TX数据源的完整流程"""
    # 1. 测试数据查询
    test_tx_data_query(setup_tx_datafeed)
    
    # 2. 测试回测
    test_tx_backtesting(setup_tx_datafeed)
    
    # 3. 测试缓存文件
    test_tx_cache_files(setup_tx_datafeed)


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])
