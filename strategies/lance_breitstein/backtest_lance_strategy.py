#!/usr/bin/env python3
"""
Lance Breitstein策略回测脚本

使用 EnhancedDataCache 统一管理数据获取和缓存：
1. 自动检查上市/退市时间，避免无效数据请求
2. 统一管理 DataFeed + AlphaLab 双缓存层
3. 自动同步元信息，保持数据一致性
"""
from datetime import datetime, timedelta
import os
import sys
import asyncio
import webbrowser
import json
import csv

from vnpy.trader.constant import Interval, Direction, Offset, Exchange
from vnpy.trader.setting import SETTINGS
from vnpy.trader.utility import extract_vt_symbol
from vnpy.trader.enhanced_data_cache import EnhancedDataCache
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.strategy.strategies.lance_breitstein_strategy import LanceBreitsteinStrategy

from tools.get_hs300_constituents import get_hs300_constituents
from tools.stock_name_mapping import get_stock_name, get_stock_code_with_name


# 设置使用tx数据源
SETTINGS["datafeed.name"] = "tx"
SETTINGS["datafeed.use_cache"] = False  # 由 EnhancedDataCache 统一管理缓存


def main():
    """主函数"""
    # 获取沪深300成分股列表
    hs300_stocks = get_hs300_constituents()
    print(f"沪深300成分股数量: {len(hs300_stocks)}")
    
    # 创建增强型数据缓存管理器（核心：统一管理 DataFeed + AlphaLab + 元信息）
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lab_path = os.path.join(project_root, "alpha_lab")
    data_cache = EnhancedDataCache(lab_path)
    
    # 打印缓存状态摘要
    cache_summary = data_cache.get_cache_summary()
    print(f"\n缓存状态摘要:")
    print(f"  - AlphaLab 路径: {cache_summary['lab_path']}")
    print(f"  - 已扫描日线: {cache_summary['scanned_daily']} 只")
    print(f"  - 已扫描分钟线: {cache_summary['scanned_minute']} 只")
    print(f"  - 股票状态分布: 完整 {cache_summary['stocks_by_status']['complete']} / "
          f"部分 {cache_summary['stocks_by_status']['partial']} / "
          f"缺失 {cache_summary['stocks_by_status']['missing']}")
    
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
    contract_json_path = os.path.join(lab_path, "contract.json")
    with open(contract_json_path, "w") as f:
        json.dump(contract_settings, f, indent=2)
    
    # 创建回测引擎
    engine = BacktestingEngine(data_cache.lab)
    
    # 设置回测参数
    vt_symbols = hs300_stocks
    interval = Interval.DAILY
    # 调整回测时间为2017-2025年（多周期MACD需要更多历史数据）
    start = datetime(2017, 1, 1)
    end = datetime(2025, 12, 31)
    capital = 1000000  # 初始资金100万
    
    engine.set_parameters(
        vt_symbols=vt_symbols,
        interval=interval,
        start=start,
        end=end,
        capital=capital
    )
    
    # 添加策略（参数与 LanceBreitsteinStrategy 新实现保持一致）
    # 选择卖出模式："condition"(传统条件模式) 或 "fixed_ratio"(固定比例止盈止损模式)
    exit_mode = "fixed_ratio"  # 默认使用固定比例模式
    
    # 策略参数（先定义，用于数据下载的回溯窗口计算）
    lookback_days = 200  # 多周期MACD需要更多历史数据
    vwap_days = 20
    long_ma = 50
    max_lookback = max(lookback_days, vwap_days, long_ma * 2)
    
    strategy_setting = {
        "lookback_days": lookback_days,
        "vwap_days": vwap_days,
        "short_ma": 10,
        "medium_ma": 20,   # MA20 —— Lance 常用回踩支撑位
        "long_ma": long_ma,    # MA50 —— Lance 常用趋势基准
        "trendline_points": 3,  # 3个摆动低点构建趋势线
        "swing_window": 5,      # 摆动点识别窗口
        "pullback_tolerance": 0.03,  # 回踩容差 3%
        "position_size": 0.1,   # 每个标的最多占总资金 10%
        "use_macd": True,              # 使用 MACD 替代均线多头判断
        "macd_fast": 12,               # MACD 快速均线周期
        "macd_slow": 26,               # MACD 慢速均线周期
        "macd_signal": 9,              # MACD 信号线周期
        "use_multi_timeframe_macd": True,  # 使用多周期MACD共振（日线+周线+月线）
        "daily_macd_relaxed": True,    # 日线条件放宽（仅需MACD>信号线，不需要连续上升）
        "weekly_macd_relaxed": True,   # 周线条件放宽（仅需MACD>信号线，不需要连续上升）
        "monthly_macd_relaxed": True,  # 月线条件放宽（仅需MACD在零轴上方）
        "allow_post_crossover": True,  # 允许周月线金叉后趋势未破状态
        "exit_mode": exit_mode,  # 卖出模式
        "take_profit_ratio": 45,  # 止盈比例 (3.5R)
        "stop_loss_ratio": 15    # 止损比例 (1R)
    }
    
    # ========== 数据获取（使用 EnhancedDataCache 统一管理）==========
    print(f"\n{'='*60}")
    print(f"开始获取 {len(vt_symbols)} 只标的数据...")
    print(f"  回测时间: {start.date()} 至 {end.date()}")
    print(f"  回溯窗口: {max_lookback} 天")
    print(f"{'='*60}")
    
    # 使用批量查询接口
    download_symbols = vt_symbols + ["000300.SSE"]  # 加入沪深300指数作为基准
    results = data_cache.batch_query(
        vt_symbols=download_symbols,
        interval=interval,
        start=start,
        end=end,
        lookback_days=max_lookback
    )
    
    # 统计查询结果
    skipped = [k for k, v in results.items() if v.skipped]
    hit_cache = [k for k, v in results.items() if v.hit_cache]
    from_source = [k for k, v in results.items() if v.from_source]
    failed = [k for k, v in results.items() if v.error]
    
    print(f"\n数据获取统计:")
    print(f"  - 跳过(上市前/退市后): {len(skipped)} 只")
    print(f"  - 命中缓存: {len(hit_cache)} 只")
    print(f"  - 从数据源获取: {len(from_source)} 只")
    print(f"  - 获取失败: {len(failed)} 只")
    
    if skipped:
        print(f"\n跳过的标的:")
        for symbol in skipped:
            reason = results[symbol].skipped_reason
            print(f"  - {symbol}: {reason}")
    
    # 过滤有效回测标的（排除被跳过的股票）
    valid_symbols = [s for s in vt_symbols if s not in skipped]
    if len(valid_symbols) < len(vt_symbols):
        print(f"\n更新有效回测标的: {len(vt_symbols)} → {len(valid_symbols)} 只")
        contract_settings = {k: v for k, v in contract_settings.items() if k in valid_symbols}
        with open(contract_json_path, "w") as f:
            json.dump(contract_settings, f, indent=2)
    
    # ========== 运行回测 ==========
    import polars as pl
    signal_df = pl.DataFrame({
        "datetime": [],
        "symbol": [],
        "signal": []
    })
    
    engine.add_strategy(LanceBreitsteinStrategy, strategy_setting, signal_df)
    engine.load_data()
    engine.run_backtesting(lookback_period=lookback_days)
    
    # ========== 计算和展示结果 ==========
    daily_df = engine.calculate_result()
    if daily_df is not None:
        print("\n回测结果：")
        print(daily_df.tail())
        
        stats = engine.calculate_statistics()
        print("\n策略统计指标：")
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # 显示策略与基准收益率对比
        print("\n显示策略与基准收益率对比...")
        engine.show_performance("000300.SSE")
        
        # 显示基本图表
        print("\n显示基本图表...")
        engine.show_chart()
        
        # 输出交易标的总结
        print("\n交易标的总结：")
        trade_data = list(engine.trades.values())
        print(f"总交易记录数: {len(trade_data)}")
        
        traded_symbols = set()
        for trade in trade_data:
            if hasattr(trade, 'vt_symbol'):
                traded_symbols.add(trade.vt_symbol)
        
        print(f"总共交易了 {len(traded_symbols)} 只标的")
        
        # 计算各标的收益和胜率
        print("\n计算各标的收益和胜率...")
        symbol_returns = {}
        symbol_win_rates = {}
        all_trades = []
        winning_trades = []
        
        for vt_symbol in traded_symbols:
            symbol_trades = [t for t in trade_data if t.vt_symbol == vt_symbol]
            symbol_trades.sort(key=lambda x: x.datetime)
            
            total_return = 0.0
            long_position = 0.0
            long_avg_price = 0.0
            short_position = 0.0
            short_avg_price = 0.0
            symbol_trade_count = 0
            symbol_win_count = 0
            
            for trade in symbol_trades:
                if trade.offset == Offset.OPEN:
                    if trade.direction == Direction.LONG:
                        total_cost = long_position * long_avg_price
                        new_cost = trade.volume * trade.price
                        long_position += trade.volume
                        if long_position > 0:
                            long_avg_price = (total_cost + new_cost) / long_position
                    elif trade.direction == Direction.SHORT:
                        total_proceeds = short_position * short_avg_price
                        new_proceeds = trade.volume * trade.price
                        short_position += trade.volume
                        if short_position > 0:
                            short_avg_price = (total_proceeds + new_proceeds) / short_position
                elif trade.offset == Offset.CLOSE:
                    profit = 0.0
                    quantity = trade.volume
                    
                    if long_position > 0:
                        close_quantity = min(quantity, long_position)
                        profit = (trade.price - long_avg_price) * close_quantity
                        total_return += profit
                        long_position -= close_quantity
                    elif short_position > 0:
                        close_quantity = min(quantity, short_position)
                        profit = (short_avg_price - trade.price) * close_quantity
                        total_return += profit
                        short_position -= close_quantity
                    
                    if profit != 0:
                        symbol_trade_count += 1
                        all_trades.append(profit)
                        if profit > 0:
                            symbol_win_count += 1
                            winning_trades.append(profit)
            
            symbol_returns[vt_symbol] = total_return
            symbol_win_rates[vt_symbol] = (symbol_win_count / symbol_trade_count * 100) if symbol_trade_count > 0 else 0.0
            print(f"{vt_symbol} 累计收益: {total_return:.2f}, 胜率: {symbol_win_rates[vt_symbol]:.2f}%")
        
        # 策略整体统计
        total_trade_count = len(all_trades)
        overall_win_rate = len(winning_trades) / total_trade_count * 100 if total_trade_count > 0 else 0.0
        avg_profit_per_trade = sum(all_trades) / total_trade_count if total_trade_count > 0 else 0.0
        avg_win_profit = sum(winning_trades) / len(winning_trades) if winning_trades else 0.0
        losing_trades = [t for t in all_trades if t < 0]
        avg_loss_profit = sum(losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        print(f"\n策略整体胜率统计：")
        print(f"总交易次数: {total_trade_count}")
        print(f"盈利交易次数: {len(winning_trades)}")
        print(f"胜率: {overall_win_rate:.2f}%")
        print(f"每笔交易平均盈利: {avg_profit_per_trade:.2f}")
        print(f"盈利交易平均盈利: {avg_win_profit:.2f}")
        print(f"亏损交易平均亏损: {avg_loss_profit:.2f}")
        
        # 保存结果
        result_dir = "backtest_results"
        os.makedirs(result_dir, exist_ok=True)
        
        # 保存标的收益统计
        returns_csv_path = os.path.join(result_dir, "symbol_returns.csv")
        with open(returns_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["标的代码", "标的名称", "累计收益", "胜率(%)", "交易次数"])
            for symbol in symbol_returns:
                total_return = symbol_returns[symbol]
                win_rate = symbol_win_rates.get(symbol, 0)
                trade_count = sum(1 for t in trade_data if t.vt_symbol == symbol)
                stock_name = get_stock_name(symbol)
                writer.writerow([symbol, stock_name, f"{total_return:.2f}", f"{win_rate:.2f}", trade_count])
        
        # 保存策略整体统计
        stats_csv_path = os.path.join(result_dir, "strategy_stats.csv")
        with open(stats_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["指标", "数值"])
            writer.writerow(["总交易次数", total_trade_count])
            writer.writerow(["盈利交易次数", len(winning_trades)])
            writer.writerow(["胜率", f"{overall_win_rate:.2f}%"])
            writer.writerow(["每笔交易平均盈利", f"{avg_profit_per_trade:.2f}"])
            writer.writerow(["盈利交易平均盈利", f"{avg_win_profit:.2f}"])
            writer.writerow(["亏损交易平均亏损", f"{avg_loss_profit:.2f}"])
        
        print(f"\n回测结果已生成：")
        print(f"- 标的收益统计：{returns_csv_path}")
        print(f"- 策略整体统计：{stats_csv_path}")


if __name__ == "__main__":
    main()
