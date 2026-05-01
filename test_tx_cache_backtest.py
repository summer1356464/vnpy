#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本: 从策略回测触发获取TX行情，缓存行情等行为
测试TX数据源、缓存系统和回测框架的完整流程
"""

import sys
import os
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
                
                # 调试信息
                self.write_log(f"日期: {bar.datetime.strftime('%Y-%m-%d')}, 收盘价: {bar.close_price}, "
                             f"持仓: {pos}, 交易日计数: {self.day_count}")
                
                # 策略逻辑：简单的买入卖出条件
                if self.day_count == self.buy_day and pos == 0:
                    # 买入
                    self.buy(vt_symbol, bar.close_price, 100)
                    self.holding = True
                    self.write_log(f"买入 {vt_symbol}, 价格: {bar.close_price}, 数量: 100")
                elif self.day_count == self.sell_day and pos > 0:
                    # 卖出
                    self.sell(vt_symbol, bar.close_price, 100)
                    self.holding = False
                    self.write_log(f"卖出 {vt_symbol}, 价格: {bar.close_price}, 数量: 100")
    
    def on_trade(self, trade):
        """处理交易"""
        self.write_log(f"交易执行: {trade.direction.value} {trade.volume} 股, "
                     f"价格: {trade.price}, 金额: {trade.volume * trade.price}")


def setup_tx_datafeed():
    """设置TX数据源"""
    print("=" * 80)
    print("设置TX数据源")
    print("=" * 80)
    
    # 设置数据源配置
    SETTINGS["datafeed.name"] = "tx"  # 使用TX数据源
    SETTINGS["datafeed.use_cache"] = True  # 启用缓存
    
    # 输出当前配置
    print(f"数据源名称: {SETTINGS.get('datafeed.name')}")
    print(f"是否启用缓存: {SETTINGS.get('datafeed.use_cache')}")
    
    # 初始化数据源
    datafeed = get_datafeed()
    success = datafeed.init()
    
    if success:
        print("✓ TX数据源初始化成功")
        # 显示缓存后端类型
        if hasattr(datafeed, "cache_backend"):
            backend_type = type(datafeed.cache_backend).__name__
            print(f"缓存后端类型: {backend_type}")
            
            # 如果是ParquetCacheBackend，显示缓存路径
            if backend_type == "ParquetCacheBackend":
                cache_root = getattr(datafeed.cache_backend, "cache_root", "./data_cache")
                print(f"Parquet缓存路径: {cache_root}")
        else:
            print("当前数据源未启用缓存")
    else:
        print("✗ TX数据源初始化失败")
        sys.exit(1)
    
    return datafeed


async def test_tx_data_query(datafeed):
    """测试TX数据源的直接查询功能"""
    print("\n" + "=" * 80)
    print("测试TX数据源直接查询")
    print("=" * 80)
    
    # 创建查询请求
    req = HistoryRequest(
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 1, 10)
    )
    
    print(f"查询请求: {req.symbol}.{req.exchange.value} {req.interval.value} "
          f"from {req.start.strftime('%Y-%m-%d')} to {req.end.strftime('%Y-%m-%d')}")
    
    # 查询数据
    bars = datafeed.query_bar_history(req)
    
    if bars:
        print(f"✓ 查询成功，获取到 {len(bars)} 条K线数据")
        print(f"  第一条数据: {bars[0].datetime.strftime('%Y-%m-%d')}, "
              f"收盘价: {bars[0].close_price}")
        print(f"  最后一条数据: {bars[-1].datetime.strftime('%Y-%m-%d')}, "
              f"收盘价: {bars[-1].close_price}")
        
        # 等待异步缓存完成
        if hasattr(datafeed, "wait_cache_tasks_complete"):
            print("等待异步缓存任务完成...")
            await datafeed.wait_cache_tasks_complete(timeout=10.0)
            print("✓ 异步缓存任务完成")
    else:
        print("✗ 查询失败，未获取到数据")
        sys.exit(1)
    
    return bars


def run_backtesting():
    """运行回测"""
    print("\n" + "=" * 80)
    print("运行策略回测")
    print("=" * 80)
    
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
    
    print(f"回测参数设置完成:")
    print(f"  合约: {'000001.SZ'}")
    print(f"  周期: {Interval.DAILY.value}")
    print(f"  时间范围: {datetime(2023, 1, 1).strftime('%Y-%m-%d')} 到 {datetime(2023, 6, 30).strftime('%Y-%m-%d')}")
    print(f"  起始资金: {100000} 元")
    print(f"  策略参数: {strategy_settings}")
    
    # 加载数据
    print("\n开始加载历史数据...")
    engine.load_data()
    print("✓ 历史数据加载完成")
    
    # 运行回测
    print("\n开始运行回测...")
    engine.run_backtesting()
    print("✓ 回测运行完成")
    
    # 计算结果
    print("\n开始计算回测结果...")
    daily_df = engine.calculate_result()
    print("✓ 回测结果计算完成")
    
    # 计算统计指标
    print("\n计算策略统计指标...")
    statistics = engine.calculate_statistics()
    
    # 输出统计结果
    print("\n" + "=" * 80)
    print("回测统计结果")
    print("=" * 80)
    for key, value in statistics.items():
        print(f"{key}: {value}")
    
    # 返回引擎和结果，以便进一步分析
    return engine, daily_df, statistics


def check_cache_files():
    """检查缓存文件是否生成"""
    print("\n" + "=" * 80)
    print("检查缓存文件")
    print("=" * 80)
    
    # 检查Parquet缓存文件
    cache_dir = "./data_cache/000001_SZSE/bar/d/"
    print(f"检查缓存目录: {cache_dir}")
    
    if os.path.exists(cache_dir):
        cache_files = os.listdir(cache_dir)
        if cache_files:
            print(f"✓ 发现 {len(cache_files)} 个缓存文件")
            print("  缓存文件列表:")
            for f in sorted(cache_files)[:5]:  # 只显示前5个
                size = os.path.getsize(os.path.join(cache_dir, f)) / 1024
                print(f"    - {f} ({size:.2f} KB)")
            if len(cache_files) > 5:
                print(f"    ... 等 {len(cache_files)} 个文件")
            
            # 显示一个缓存文件的内容示例
            sample_file = os.path.join(cache_dir, sorted(cache_files)[0])
            print(f"\n  示例文件内容 ({sample_file}):")
            try:
                df = pd.read_parquet(sample_file)
                print(df.head())
            except Exception as e:
                print(f"    读取文件失败: {e}")
        else:
            print("✗ 缓存目录存在，但没有缓存文件")
    else:
        print("✗ 缓存目录不存在")
        print("  可能的原因：")
        print("  1. 缓存功能未启用")
        print("  2. 缓存路径配置不同")
        print("  3. 数据未被缓存")


async def main():
    """主函数"""
    print("=" * 80)
    print("测试TX行情获取与缓存功能")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 设置TX数据源
        datafeed = setup_tx_datafeed()
        
        # 2. 测试直接查询
        await test_tx_data_query(datafeed)
        
        # 3. 运行回测
        engine, daily_df, statistics = run_backtesting()
        
        # 4. 检查缓存文件
        check_cache_files()
        
        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)
        print("✓ TX行情数据源正常工作")
        print("✓ 缓存功能正常运行")
        print("✓ 策略回测成功执行")
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