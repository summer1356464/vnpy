#!/usr/bin/env python3
"""
Lance Breitstein策略回测脚本
"""
from datetime import datetime
import os
import sys
import asyncio

from vnpy.trader.constant import Interval, Direction, Offset
from vnpy.trader.setting import SETTINGS
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest
from vnpy.trader.utility import extract_vt_symbol
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.strategy.strategies.lance_breitstein_strategy import LanceBreitsteinStrategy

from tools.get_hs300_constituents import get_hs300_constituents


# 设置使用tx数据源和缓存
SETTINGS["datafeed.name"] = "tx"
SETTINGS["datafeed.use_cache"] = True
SETTINGS["datafeed.cache_path"] = "./data_cache"  # 设置缓存目录


async def download_data(datafeed, lab, vt_symbols, interval, start, end):
    """异步下载数据"""
    print("\n开始检查并下载历史数据...")
    
    # 下载标的数据
    for vt_symbol in vt_symbols:
        # 先检查AlphaLab中是否已有数据
        existing_bars = lab.load_bar_data(vt_symbol, interval, start, end)
        if existing_bars and len(existing_bars) > 0:
            print(f"✓ {vt_symbol} 在AlphaLab中已有数据 ({len(existing_bars)}条)，跳过下载")
            continue
        
        symbol, exchange = extract_vt_symbol(vt_symbol)
        
        # 创建历史数据请求
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=start,
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
    # 先检查AlphaLab中是否已有数据
    existing_hs300_bars = lab.load_bar_data(hs300_symbol, interval, start, end)
    if existing_hs300_bars and len(existing_hs300_bars) > 0:
        print(f"✓ 沪深300指数在AlphaLab中已有数据 ({len(existing_hs300_bars)}条)，跳过下载")
    else:
        print("\n下载沪深300指数数据用于基准对比...")
        hs300_symbol_clean, hs300_exchange = extract_vt_symbol(hs300_symbol)
        
        # 创建历史数据请求
        hs300_req = HistoryRequest(
            symbol=hs300_symbol_clean,
            exchange=hs300_exchange,
            interval=interval,
            start=start,
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
    
    # 等待所有异步缓存任务完成
    await asyncio.sleep(1)

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
    start = datetime(2024, 1, 1)
    end = datetime(2025, 12, 31)
    capital = 1000000  # 初始资金100万
    
    # 异步下载全量沪深300成分股数据
    print(f"\n开始下载全量 {len(vt_symbols)} 只沪深300成分股数据...")
    asyncio.run(download_data(datafeed, lab, vt_symbols, interval, start, end))
    
    engine.set_parameters(
        vt_symbols=vt_symbols,  # 使用全量沪深300成分股
        interval=interval,
        start=start,
        end=end,
        capital=capital
    )
    
    # 添加策略（参数与 LanceBreitsteinStrategy 新实现保持一致）
    strategy_setting = {
        "lookback_days": 120,
        "vwap_days": 20,
        "short_ma": 10,
        "medium_ma": 20,   # MA20 —— Lance 常用回踩支撑位
        "long_ma": 50,    # MA50 —— Lance 常用趋势基准
        "trendline_points": 3,  # 3个摆动低点构建趋势线
        "swing_window": 5,      # 摆动点识别窗口
        "pullback_tolerance": 0.03,  # 回踩容差 3%
        "position_size": 0.1   # 每个标的最多占总资金 10%
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
        
        # 显示策略与基准收益率对比（沪深300指数）
        print("\n显示策略与基准收益率对比...")
        engine.show_performance("000300.SSE")  # 沪深300指数
        
        # 显示基本图表
        print("\n显示基本回测图表...")
        engine.show_chart()
        
        # 输出交易标的总结
        print("\n交易标的总结：")
        traded_symbols = set()
        for trade in engine.trades.values():
            traded_symbols.add(trade.vt_symbol)
        
        print(f"总共交易了 {len(traded_symbols)} 只标的")
        print(f"交易标的列表：{list(traded_symbols)}")
        
        # 计算每个标的的累计收益
        print("\n计算各标的收益...")
        symbol_returns = {}
        
        for vt_symbol in traded_symbols:
            symbol_trades = [trade for trade in engine.trades.values() if trade.vt_symbol == vt_symbol]
            symbol_trades.sort(key=lambda x: x.datetime)
            
            # 计算该标的的累计收益
            total_return = 0.0
            position = 0.0  # 当前持仓量
            avg_entry_price = 0.0  # 平均持仓成本
            
            for trade in symbol_trades:
                if trade.direction == Direction.LONG:
                    if trade.offset == Offset.OPEN:
                        # 开仓
                        total_cost = position * avg_entry_price
                        new_cost = trade.volume * trade.price
                        position += trade.volume
                        avg_entry_price = (total_cost + new_cost) / position
                    elif trade.offset == Offset.CLOSE:
                        # 平仓
                        if position > 0:
                            close_quantity = min(trade.volume, position)
                            profit = (trade.price - avg_entry_price) * close_quantity
                            total_return += profit
                            position -= close_quantity
                            # 如果还有剩余持仓，重新计算平均成本
                            if position > 0:
                                # 这里简化处理，实际应该更精确计算
                                pass
                
            symbol_returns[vt_symbol] = total_return
            print(f"{vt_symbol} 累计收益: {total_return:.2f}")
        
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
        
        # 绘制带有买卖点标注的K线图
        from vnpy.trader.object import BarData
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        def plot_symbol_with_signals(vt_symbol, bars, trades, total_return):
            """绘制单个标的的K线图并标注买卖点"""
            # 准备K线数据
            dates = [bar.datetime for bar in bars]
            opens = [bar.open_price for bar in bars]
            highs = [bar.high_price for bar in bars]
            lows = [bar.low_price for bar in bars]
            closes = [bar.close_price for bar in bars]
            volumes = [bar.volume for bar in bars]
            
            # 准备买卖信号数据
            buy_dates = []
            buy_prices = []
            sell_dates = []
            sell_prices = []
            
            for trade in trades:
                if trade.direction == Direction.LONG:
                    buy_dates.append(trade.datetime)
                    buy_prices.append(trade.price)
                else:
                    sell_dates.append(trade.datetime)
                    sell_prices.append(trade.price)
            
            # 创建图表
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.03, 
                               row_heights=[0.8, 0.2])
            
            # 添加K线图
            fig.add_trace(
                go.Candlestick(x=dates, 
                              open=opens, 
                              high=highs, 
                              low=lows, 
                              close=closes, 
                              name="K线"),
                row=1, col=1
            )
            
            # 添加成交量柱状图
            fig.add_trace(
                go.Bar(x=dates, y=volumes, name="成交量"),
                row=2, col=1
            )
            
            # 添加买入信号（绿色三角形，向上）
            if buy_dates:
                fig.add_trace(
                    go.Scatter(x=buy_dates, 
                              y=buy_prices, 
                              mode="markers", 
                              marker=dict(color="green", symbol="triangle-up", size=10), 
                              name="买入"),
                    row=1, col=1
                )
            
            # 添加卖出信号（红色三角形，向下）
            if sell_dates:
                fig.add_trace(
                    go.Scatter(x=sell_dates, 
                              y=sell_prices, 
                              mode="markers", 
                              marker=dict(color="red", symbol="triangle-down", size=10), 
                              name="卖出"),
                    row=1, col=1
                )
            
            # 设置图表布局
            fig.update_layout(title=f"{vt_symbol} K线图及买卖点标注 (累计收益: {total_return:.2f})")
            
            # 显示图表
            fig.show()
        
        # 为选中的标的绘制K线图
        print("\n绘制选中标的的K线图及买卖点标注...")
        for vt_symbol in selected_symbols:
            # 获取该标的的K线数据
            symbol_bars = []
            for dt in sorted(engine.dts):
                bar = engine.history_data.get((dt, vt_symbol))
                if bar:
                    symbol_bars.append(bar)
            
            # 获取该标的的交易记录
            symbol_trades = [trade for trade in engine.trades.values() if trade.vt_symbol == vt_symbol]
            
            if symbol_bars and symbol_trades:
                total_return = symbol_returns[vt_symbol]
                print(f"绘制 {vt_symbol} 的K线图 (收益: {total_return:.2f})...")
                plot_symbol_with_signals(vt_symbol, symbol_bars, symbol_trades, total_return)


if __name__ == "__main__":
    main()
