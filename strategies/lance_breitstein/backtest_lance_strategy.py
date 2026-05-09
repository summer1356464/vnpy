#!/usr/bin/env python3
"""
Lance Breitstein策略回测脚本
"""
from datetime import datetime
import os
import sys
import asyncio
import webbrowser

from vnpy.trader.constant import Interval, Direction, Offset
from vnpy.trader.setting import SETTINGS
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest
from vnpy.trader.utility import extract_vt_symbol
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.strategy.strategies.lance_breitstein_strategy import LanceBreitsteinStrategy

from tools.get_hs300_constituents import get_hs300_constituents


# 设置使用tx数据源（不使用缓存包装，让AlphaLab处理数据存储）
SETTINGS["datafeed.name"] = "tx"
SETTINGS["datafeed.use_cache"] = False  # 关闭缓存包装，直接使用TX数据源
# AlphaLab将使用其原生Parquet格式存储数据（按标的存储）


def download_data(datafeed, lab, vt_symbols, interval, start, end, lookback_days: int = 120):
    """
    下载数据
    :param lookback_days: 回溯窗口天数，用于计算指标需要的额外历史数据
    """
    # 计算实际的下载开始日期（向前推lookback_days天，用于计算指标）
    from datetime import timedelta
    actual_start = start - timedelta(days=lookback_days)
    
    print(f"\n开始检查并下载历史数据...")
    print(f"  回测时间范围: {start.date()} 至 {end.date()}")
    print(f"  下载时间范围: {actual_start.date()} 至 {end.date()} (包含{lookback_days}天回溯窗口)")
    
    # 下载标的数据
    for vt_symbol in vt_symbols:
        # 先检查AlphaLab中是否已有足够的数据（包含回溯窗口）
        existing_bars = lab.load_bar_data(vt_symbol, interval, actual_start, end)
        
        # 检查缓存数据是否完全覆盖请求的时间范围
        need_download = True
        if existing_bars and len(existing_bars) > 0:
            # 获取缓存数据的实际时间范围
            bar_dates = [b.datetime for b in existing_bars]
            cache_start = min(bar_dates)
            cache_end = max(bar_dates)
            
            # 检查缓存是否完全覆盖请求范围
            if cache_start <= actual_start and cache_end >= end:
                print(f"✓ {vt_symbol} 在AlphaLab中已有完整数据 ({len(existing_bars)}条，{cache_start.date()}至{cache_end.date()})，跳过下载")
                need_download = False
            else:
                print(f"⚠ {vt_symbol} 缓存数据不完整 (缓存: {cache_start.date()}至{cache_end.date()}, 需要: {actual_start.date()}至{end.date()})，重新下载")
        
        if not need_download:
            continue
        
        symbol, exchange = extract_vt_symbol(vt_symbol)
        
        # 创建历史数据请求（使用包含回溯窗口的开始日期）
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=actual_start,
            end=end
        )
        
        # 从数据源获取数据（数据源会自动使用TX+Cache缓存）
        bars = datafeed.query_bar_history(req)
        
        if bars:
            print(f"✓ 从数据源获取 {vt_symbol} 数据成功 ({len(bars)}条)")
            # 保存到AlphaLab
            lab.save_bar_data(bars)
        else:
            print(f"✗ 未获取到 {vt_symbol} 数据")
    
    # 下载沪深300指数数据用于基准对比
    hs300_symbol = "000300.SSE"
    # 先检查AlphaLab中是否已有数据（包含回溯窗口）
    existing_hs300_bars = lab.load_bar_data(hs300_symbol, interval, actual_start, end)
    if existing_hs300_bars and len(existing_hs300_bars) > 0:
        print(f"✓ 沪深300指数在AlphaLab中已有数据 ({len(existing_hs300_bars)}条)，跳过下载")
    else:
        print("\n下载沪深300指数数据用于基准对比...")
        hs300_symbol_clean, hs300_exchange = extract_vt_symbol(hs300_symbol)
        
        # 创建历史数据请求（使用包含回溯窗口的开始日期）
        hs300_req = HistoryRequest(
            symbol=hs300_symbol_clean,
            exchange=hs300_exchange,
            interval=interval,
            start=actual_start,
            end=end
        )
        
        # 从数据源获取数据（数据源会自动使用TX+Cache缓存）
        hs300_bars = datafeed.query_bar_history(hs300_req)
        
        if hs300_bars:
            print(f"✓ 从数据源获取沪深300指数数据成功 ({len(hs300_bars)}条)")
            # 保存到AlphaLab
            lab.save_bar_data(hs300_bars)
        else:
            print(f"✗ 未获取到沪深300指数数据")

def main():
    """主函数"""
    # 获取沪深300成分股列表
    hs300_stocks = get_hs300_constituents()
    print(f"沪深300成分股数量: {len(hs300_stocks)}")
    
    # 获取默认数据源（tx+cache）
    datafeed = get_datafeed()
    
    # 创建AlphaLab实例，使用项目根目录下的alpha_lab
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lab_path = os.path.join(project_root, "alpha_lab")
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
    vt_symbols = hs300_stocks  # 使用已经下载数据的所有沪深300成分股进行回测
    interval = Interval.DAILY
    # 调整回测时间为2024-2025年
    start = datetime(2022, 1, 1)
    end = datetime(2025, 12, 31)
    capital = 1000000  # 初始资金100万
    
    engine.set_parameters(
        vt_symbols=vt_symbols,  # 使用全量沪深300成分股
        interval=interval,
        start=start,
        end=end,
        capital=capital
    )
    
    # 添加策略（参数与 LanceBreitsteinStrategy 新实现保持一致）
    # 选择卖出模式："condition"(传统条件模式) 或 "fixed_ratio"(固定比例止盈止损模式)
    exit_mode = "fixed_ratio"  # 默认使用固定比例模式
    
    # 策略参数（先定义，用于数据下载的回溯窗口计算）
    lookback_days = 120
    vwap_days = 20
    long_ma = 50
    
    # 计算需要的最大回溯窗口（确保所有指标都能计算）
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
        "exit_mode": exit_mode,  # 卖出模式
        "take_profit_ratio": 45,  # 止盈比例 (3.5R)
        "stop_loss_ratio": 15    # 止损比例 (1R)
    }
    
    # 下载全量沪深300成分股和基准指数数据（包含回溯窗口）
    benchmark_symbol = "000300.SSE"  # 沪深300指数作为基准
    download_symbols = vt_symbols + [benchmark_symbol]  # 加入基准指数到下载列表
    print(f"\n开始下载 {len(download_symbols)} 只标的数据（含 {len(vt_symbols)} 只成分股 + 1只基准指数）...")
    download_data(datafeed, lab, download_symbols, interval, start, end, max_lookback)
    
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
        
        # 显示策略与基准收益率对比（沪深300指数）
        print("\n显示策略与基准收益率对比...")
        engine.show_performance("000300.SSE")  # 沪深300指数
        
        # 显示基本图表
        print("\n显示基本图表...")
        engine.show_chart()
        
        # 输出交易标的总结
        print("\n交易标的总结：")
        traded_symbols = set()
        
        # 直接使用engine.trades.values()，因为我们已经确认它包含交易记录
        trade_data = engine.trades.values()
        
        print(f"engine.trades.values() 包含 {len(trade_data)} 条交易记录")
        
        # 显示前几个交易记录的vt_symbol属性
        print("\n前5个交易记录的vt_symbol：")
        for i, trade in enumerate(trade_data):
            if i >= 5:
                break
            print(f"  交易 {i+1}: vt_symbol = {trade.vt_symbol if hasattr(trade, 'vt_symbol') else '无此属性'}")
            traded_symbols.add(trade.vt_symbol)
        
        # 处理剩余的交易记录
        for trade in list(trade_data)[5:]:
            if hasattr(trade, 'vt_symbol'):
                traded_symbols.add(trade.vt_symbol)
        
        print(f"总共交易了 {len(traded_symbols)} 只标的")
        print(f"交易标的列表：{list(traded_symbols)}")
        
        # 计算每个标的的累计收益和胜率
        print("\n计算各标的收益和胜率...")
        symbol_returns = {}
        symbol_win_rates = {}
        all_trades = []
        winning_trades = []
        
        # 直接使用engine.trades.values()，因为我们已经确认它包含交易记录
        all_trades_data = list(engine.trades.values())
        
        for vt_symbol in traded_symbols:
            # 获取该标的的所有交易记录
            symbol_trades = [trade for trade in all_trades_data if trade.vt_symbol == vt_symbol]
            symbol_trades.sort(key=lambda x: x.datetime)
            
            # 计算该标的的累计收益和胜率
            total_return = 0.0
            long_position = 0.0  # 多头持仓量
            long_avg_price = 0.0  # 多头平均成本
            short_position = 0.0  # 空头持仓量
            short_avg_price = 0.0  # 空头平均成本
            symbol_trade_count = 0
            symbol_win_count = 0
            
            for trade in symbol_trades:
                if trade.offset == Offset.OPEN:
                    # 开仓操作
                    if trade.direction == Direction.LONG:
                        # 多头开仓
                        total_cost = long_position * long_avg_price
                        new_cost = trade.volume * trade.price
                        long_position += trade.volume
                        if long_position > 0:
                            long_avg_price = (total_cost + new_cost) / long_position
                    elif trade.direction == Direction.SHORT:
                        # 空头开仓
                        total_proceeds = short_position * short_avg_price
                        new_proceeds = trade.volume * trade.price
                        short_position += trade.volume
                        if short_position > 0:
                            short_avg_price = (total_proceeds + new_proceeds) / short_position
                elif trade.offset == Offset.CLOSE:
                    # 平仓操作
                    profit = 0.0
                    quantity = trade.volume
                    
                    # 关键修复：根据当前持仓情况判断平仓方向，而非依赖交易的direction
                    if long_position > 0:
                        # 有多头持仓，进行多头平仓
                        close_quantity = min(quantity, long_position)
                        profit = (trade.price - long_avg_price) * close_quantity
                        total_return += profit
                        long_position -= close_quantity
                    elif short_position > 0:
                        # 有空头持仓，进行空头平仓
                        close_quantity = min(quantity, short_position)
                        profit = (short_avg_price - trade.price) * close_quantity
                        total_return += profit
                        short_position -= close_quantity
                    
                    # 统计胜率
                    if profit != 0:
                        symbol_trade_count += 1
                        all_trades.append(profit)
                        if profit > 0:
                            symbol_win_count += 1
                            winning_trades.append(profit)
            
            symbol_returns[vt_symbol] = total_return
            
            # 计算该标的胜率
            if symbol_trade_count > 0:
                symbol_win_rate = symbol_win_count / symbol_trade_count * 100
            else:
                symbol_win_rate = 0.0
            symbol_win_rates[vt_symbol] = symbol_win_rate
            
            print(f"{vt_symbol} 累计收益: {total_return:.2f}, 胜率: {symbol_win_rate:.2f}%")
        
        # 计算策略整体胜率
        total_trade_count = len(all_trades)
        if total_trade_count > 0:
            overall_win_rate = len(winning_trades) / total_trade_count * 100
            avg_profit_per_trade = sum(all_trades) / total_trade_count
            avg_win_profit = sum(winning_trades) / len(winning_trades) if winning_trades else 0
            losing_trades = [t for t in all_trades if t < 0]
            avg_loss_profit = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        else:
            overall_win_rate = 0.0
            avg_profit_per_trade = 0.0
            avg_win_profit = 0.0
            avg_loss_profit = 0.0
        
        print(f"\n策略整体胜率统计：")
        print(f"总交易次数: {total_trade_count}")
        print(f"盈利交易次数: {len(winning_trades)}")
        print(f"胜率: {overall_win_rate:.2f}%")
        print(f"每笔交易平均盈利: {avg_profit_per_trade:.2f}")
        print(f"盈利交易平均盈利: {avg_win_profit:.2f}")
        print(f"亏损交易平均亏损: {avg_loss_profit:.2f}")
        
        # 按收益排序标的
        sorted_symbols = sorted(symbol_returns.items(), key=lambda x: x[1], reverse=True)
        
        # 选择要展示的标的：收益最高10个、最低10个、中位收益10个
        top_10 = sorted_symbols[:10]
        bottom_10 = sorted_symbols[-10:]
        
        # 选择中位收益附近的10个标的
        total_traded = len(sorted_symbols)
        mid_idx = total_traded // 2
        mid_10_start = max(0, mid_idx - 5)
        mid_10_end = min(total_traded, mid_idx + 5)
        mid_10 = sorted_symbols[mid_10_start:mid_10_end]
        
        # 合并要展示的标的列表
        selected_symbols = [symbol for symbol, _ in top_10 + bottom_10 + mid_10]
        # 去重
        selected_symbols = list(dict.fromkeys(selected_symbols))
        
        print(f"\n选择展示的标的：")
        print(f"收益最高10个: {[symbol for symbol, _ in top_10]}")
        print(f"收益最低10个: {[symbol for symbol, _ in bottom_10]}")
        print(f"中位收益10个: {[symbol for symbol, _ in mid_10]}")
        print(f"总共展示 {len(selected_symbols)} 个标的")
        
        # 保存简单的回测结果统计
        result_dir = "backtest_results"
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
        
        # 保存详细的交易记录和收益统计到CSV文件
        import csv
        
        # 保存标的收益统计
        returns_csv_path = os.path.join(result_dir, "symbol_returns.csv")
        with open(returns_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["标的代码", "累计收益", "胜率(%)", "交易次数"])
            for symbol in symbol_returns:
                total_return = symbol_returns[symbol]
                win_rate = symbol_win_rates.get(symbol, 0)
                trade_count = sum(1 for trade in engine.trades.values() if trade.vt_symbol == symbol)
                writer.writerow([symbol, f"{total_return:.2f}", f"{win_rate:.2f}", trade_count])
        
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
        
        # 生成包含K线图的HTML报告（只显示前3个示例）
        from vnpy.trader.object import BarData
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import plotly.offline as pyo
        
        # 只显示前3个标的的K线图作为示例
        sample_symbols = top_10[:3] + bottom_10[:3] + mid_10[:3]
        
        # 获取当前测试时间
        test_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lance策略回测结果</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                .stats {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 30px; }}
                .stats table {{ width: 100%; border-collapse: collapse; }}
                .stats th, .stats td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .stats th {{ background-color: #4CAF50; color: white; }}
                .section {{ margin-bottom: 30px; }}
                .symbol-list {{ background-color: white; padding: 15px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 15px; }}
                .chart-container {{ background-color: white; padding: 20px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 40px; }}
                .chart {{ width: 100%; height: 500px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>Lance Breitstein策略回测结果</h1>
            
            <div class="stats">
                <h2>策略整体统计</h2>
                <table>
                    <tr><th>指标</th><th>数值</th></tr>
                    <tr><td>测试时间</td><td>{test_time}</td></tr>
                    <tr><td>总交易次数</td><td>{total_trade_count}</td></tr>
                    <tr><td>盈利交易次数</td><td>{len(winning_trades)}</td></tr>
                    <tr><td>胜率</td><td>{overall_win_rate:.2f}%</td></tr>
                    <tr><td>每笔交易平均盈利</td><td>{avg_profit_per_trade:.2f}</td></tr>
                    <tr><td>盈利交易平均盈利</td><td>{avg_win_profit:.2f}</td></tr>
                    <tr><td>亏损交易平均亏损</td><td>{avg_loss_profit:.2f}</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h2>回测结果说明</h2>
                <p>本次回测共分析了 {len(symbol_returns)} 个标的，以下是收益排名情况：</p>
            </div>
            
            <div class="section">
                <h3>收益最高10个标的</h3>
                <div class="symbol-list">
                    <ul>
                        {''.join([f'<li>{symbol} (收益: {return_val:.2f}, 胜率: {symbol_win_rates[symbol]:.2f}%)</li>' for symbol, return_val in top_10])}
                    </ul>
                </div>
            </div>
            
            <div class="section">
                <h3>中位收益10个标的</h3>
                <div class="symbol-list">
                    <ul>
                        {''.join([f'<li>{symbol} (收益: {return_val:.2f}, 胜率: {symbol_win_rates[symbol]:.2f}%)</li>' for symbol, return_val in mid_10])}
                    </ul>
                </div>
            </div>
            
            <div class="section">
                <h3>收益最低10个标的</h3>
                <div class="symbol-list">
                    <ul>
                        {''.join([f'<li>{symbol} (收益: {return_val:.2f}, 胜率: {symbol_win_rates[symbol]:.2f}%)</li>' for symbol, return_val in bottom_10])}
                    </ul>
                </div>
            </div>
            
            <div class="section">
                <h2>K线图展示（示例标的）</h2>
                <p>以下是部分标的的K线图和买卖信号标记（仅显示收益最高、最低和中位各3个标的）：</p>
            </div>"""
        
        # 为示例标的绘制K线图
        chart_htmls = []
        for i, (symbol, return_val) in enumerate(sample_symbols):
            # 获取该标的的K线数据
            symbol_bars = []
            if hasattr(engine, 'history_data') and hasattr(engine, 'dts'):
                for dt in sorted(engine.dts):
                    bar = engine.history_data.get((dt, symbol))
                    if bar:
                        symbol_bars.append(bar)
            
            if not symbol_bars:
                continue
            
            # 获取该标的的交易记录
            symbol_trades = [trade for trade in engine.trades.values() if trade.vt_symbol == symbol]
            
            if symbol_bars and symbol_trades:
                total_return = symbol_returns[symbol]
                win_rate = symbol_win_rates[symbol]
                
                print(f"绘制示例K线图: {symbol} (收益: {total_return:.2f}, 胜率: {win_rate:.2f}%)...")
                
                # 准备K线数据
                dates = [bar.datetime for bar in symbol_bars]
                opens = [bar.open_price for bar in symbol_bars]
                highs = [bar.high_price for bar in symbol_bars]
                lows = [bar.low_price for bar in symbol_bars]
                closes = [bar.close_price for bar in symbol_bars]
                volumes = [bar.volume for bar in symbol_bars]
                
                # 准备买卖信号数据
                buy_dates = []
                buy_prices = []
                sell_dates = []
                sell_prices = []
                
                for trade in symbol_trades:
                    if trade.direction == Direction.LONG:
                        buy_dates.append(trade.datetime)
                        buy_prices.append(trade.price)
                    else:
                        sell_dates.append(trade.datetime)
                        sell_prices.append(trade.price)
                
                # 创建图表
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
                
                # 添加K线图
                fig.add_trace(
                    go.Candlestick(x=dates, open=opens, high=highs, low=lows, close=closes, name="K线"),
                    row=1, col=1
                )
                
                # 添加成交量
                fig.add_trace(go.Bar(x=dates, y=volumes, name="成交量"), row=2, col=1)
                
                # 添加买卖信号
                if buy_dates:
                    fig.add_trace(go.Scatter(x=buy_dates, y=buy_prices, mode="markers", 
                                           marker=dict(color="green", symbol="triangle-up", size=10), 
                                           name="买入"), row=1, col=1)
                if sell_dates:
                    fig.add_trace(go.Scatter(x=sell_dates, y=sell_prices, mode="markers", 
                                           marker=dict(color="red", symbol="triangle-down", size=10), 
                                           name="卖出"), row=1, col=1)
                
                # 设置布局
                fig.update_layout(title=f"{symbol} K线图 (收益: {total_return:.2f}, 胜率: {win_rate:.2f}%)", 
                                 height=500, width=1000)
                
                # 添加图表到HTML
                graph_html = pyo.plot(fig, include_plotlyjs=False, output_type='div')
                chart_htmls.append(f"<div class='chart-container'>{graph_html}</div>")
        
        # 添加图表HTML到主内容
        html_content += ''.join(chart_htmls)
        
        # 添加详细数据下载部分
        html_content += f"""
            <div class="section">
                <h2>详细数据下载</h2>
                <p>所有标的的完整收益统计已保存至CSV文件：</p>
                <ul>
                    <li><strong>标的收益统计</strong>：<code>{returns_csv_path}</code></li>
                    <li><strong>策略整体统计</strong>：<code>{stats_csv_path}</code></li>
                </ul>
                <p>您可以使用Excel、Google Sheets或其他数据分析工具打开这些文件查看详细数据。</p>
            </div>
        </body>
        </html>
        """
        
        # 保存HTML文件
        html_file_path = os.path.join(result_dir, "lance_backtest_results.html")
        with open(html_file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\n回测结果已生成：")
        print(f"- HTML报告：{html_file_path}")
        print(f"- 标的收益统计：{returns_csv_path}")
        print(f"- 策略整体统计：{stats_csv_path}")
        
        # 自动打开HTML报告
        html_file_url = f"file://{os.path.abspath(html_file_path)}"
        print(f"\n正在打开HTML报告...")
        webbrowser.open(html_file_url)


if __name__ == "__main__":
    main()
