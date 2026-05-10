#!/usr/bin/env python3
"""
K线图表CLI工具
支持从命令行快速打开K线图表
"""
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Callable
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest
from vnpy.trader.setting import SETTINGS
from chart_wrapper import plot_bars, create_chart

# 尝试导入AKShare
try:
    import akshare as ak
    AK_SHARE_AVAILABLE = True
except ImportError:
    print("警告：未安装AKShare库，将使用模拟数据", file=sys.stderr)
    AK_SHARE_AVAILABLE = False


class SimpleTXDatafeed:
    """
    简化版TX数据源实现，直接使用AKShare获取数据
    """
    
    def __init__(self):
        """初始化数据源"""
        self.inited = False
    
    def init(self, output: Callable = print) -> bool:
        """初始化数据源"""
        if not AK_SHARE_AVAILABLE:
            output("AKShare未安装，无法初始化TX数据源")
            return False
        
        self.inited = True
        output("TX数据源初始化成功")
        return True
    
    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> List[BarData]:
        """
        查询历史K线数据
        """
        if not self.inited:
            if not self.init(output):
                return []
        
        try:
            # 腾讯财经API只支持日线数据
            if req.interval != Interval.DAILY:
                output("警告：腾讯财经API仅支持日线数据，已自动切换为日线")
                req.interval = Interval.DAILY
            
            # 转换为腾讯财经所需的代码格式
            if req.exchange == Exchange.SSE:
                ak_symbol = f"sh{req.symbol}"
            elif req.exchange == Exchange.SZSE:
                ak_symbol = f"sz{req.symbol}"
            else:
                output(f"不支持的交易所：{req.exchange}")
                return []
            
            # 转换时间格式
            start_date = req.start.strftime("%Y%m%d")
            end_date = req.end.strftime("%Y%m%d") if req.end else datetime.now().strftime("%Y%m%d")
            
            output(f"正在从腾讯财经获取{req.symbol}的日线数据...")
            
            # 下载历史数据
            df = ak.stock_zh_a_hist_tx(
                symbol=ak_symbol,
                start_date=start_date,
                end_date=end_date,
                adjust="hfq"  # 后复权
            )
            
            if df.empty:
                output(f"未获取到{req.symbol}的K线数据")
                return []
            

            
            # 转换为BarData列表
            bars: List[BarData] = []
            for _, row in df.iterrows():
                bar = BarData(
                    symbol=req.symbol,
                    exchange=req.exchange,
                    datetime=datetime.combine(row["date"], datetime.min.time()),
                    interval=req.interval,
                    volume=int(row.get("volume", 0)) if "volume" in row else 0,  # 尝试直接获取成交量
                    turnover=float(row.get("amount", 0)),
                    open_interest=0,
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                    gateway_name="TX"
                )
                
                # 如果没有直接的成交量数据，根据成交额和收盘价计算
                if bar.volume == 0 and bar.close_price > 0:
                    bar.volume = round(bar.turnover / bar.close_price, 0)
                
                bars.append(bar)
            
            output(f"成功获取{len(bars)}条K线数据")
            return bars
            
        except Exception as e:
            output(f"获取K线数据失败：{e}")
            # 如果真实数据获取失败，使用模拟数据
            return self._generate_sample_bars(req, output)
    
    def _generate_sample_bars(self, req: HistoryRequest, output: Callable = print) -> List[BarData]:
        """
        生成模拟K线数据
        """
        output(f"正在生成{req.symbol}的模拟K线数据...")
        
        bars = []
        time_delta = timedelta(days=1)
        current_dt = req.start
        
        # 根据股票代码生成不同的基础价格
        base_prices = {
            "000001": 10.0,
            "600000": 8.0,
            "600519": 1800.0,
            "002415": 30.0,
            "IF888": 4000.0
        }
        
        base_price = base_prices.get(req.symbol, 15.0)
        
        for i in range(90):  # 生成90天的数据
            if current_dt > req.end:
                break
            
            # 生成模拟价格
            open_price = base_price + (i * 0.01) + (i % 10) * 0.05
            high_price = open_price + 0.5 + (i % 5) * 0.1
            low_price = open_price - 0.2 - (i % 3) * 0.05
            close_price = low_price + (high_price - low_price) * 0.7 + (i % 4) * 0.05
            
            bar = BarData(
                symbol=req.symbol,
                exchange=req.exchange,
                datetime=current_dt,
                interval=req.interval,
                volume=i * 10000,
                turnover=close_price * i * 10000,
                open_interest=1000000 + i * 10000 if "IF" in req.symbol else 0,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                gateway_name="SAMPLE"
            )
            
            bars.append(bar)
            current_dt += time_delta
        
        output(f"成功生成{len(bars)}条模拟K线数据")
        return bars


def get_bar_data(symbol: str, 
                 exchange: Exchange, 
                 interval: Interval, 
                 days: int = 90) -> List[BarData]:
    """
    获取K线数据（直接从TX数据源获取）
    
    Args:
        symbol: 股票代码
        exchange: 交易所
        interval: 时间周期
        days: 数据天数
        
    Returns:
        BarData对象列表
    """
    # 计算时间范围
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    
    # 创建历史数据请求
    req = HistoryRequest(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        start=start_dt,
        end=end_dt
    )
    
    # 创建并初始化数据源
    datafeed = SimpleTXDatafeed()
    datafeed.init()
    
    # 查询数据
    bars = datafeed.query_bar_history(req)
    
    return bars


def parse_interval(interval_str: str) -> Interval:
    """
    解析时间周期字符串
    
    Args:
        interval_str: 时间周期字符串 (1m, 5m, 1h, 1d, 1w)
        
    Returns:
        Interval枚举值
    """
    # 使用VNPY支持的标准Interval枚举值
    interval_map = {
        "1m": Interval.MINUTE,
        "1h": Interval.HOUR,
        "1d": Interval.DAILY,
        "1w": Interval.WEEKLY
    }
    
    return interval_map.get(interval_str.lower(), Interval.DAILY)


def parse_exchange(symbol: str) -> Exchange:
    """
    根据股票代码解析交易所
    
    Args:
        symbol: 股票代码
        
    Returns:
        Exchange枚举值
    """
    if symbol == "000001":
        return Exchange.SSE  # 上证指数是上交所指数
    elif symbol.startswith("001") or symbol.startswith("002") or symbol.startswith("300"):
        return Exchange.SZSE  # 深圳交易所股票
    elif symbol.startswith("600") or symbol.startswith("601") or symbol.startswith("603") or symbol.startswith("000"):
        return Exchange.SSE  # 上海交易所股票和指数
    elif symbol.startswith("IF") or symbol.startswith("IC") or symbol.startswith("IH"):
        return Exchange.CFFEX  # 中金所
    else:
        return Exchange.SSE  # 默认上海交易所


def main():
    """
    CLI工具主函数
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="K线图表CLI工具")
    
    # 必选参数：股票代码
    parser.add_argument("symbol", 
                        help="股票代码，如：000001、600000、IF888")
    
    # 可选参数：时间周期
    parser.add_argument("-i", "--interval", 
                        default="1d",
                        choices=["1m", "1h", "1d", "1w"],
                        help="时间周期，默认：1d (日线)")
    
    # 可选参数：数据天数
    parser.add_argument("-d", "--days", 
                        type=int,
                        default=90,
                        help="数据天数，默认：90天")
    
    # 可选参数：是否显示成交量
    parser.add_argument("--no-volume", 
                        action="store_true",
                        help="不显示成交量")
    
    # 可选参数：图表标题
    parser.add_argument("-t", "--title", 
                        help="图表标题")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    try:
        # 解析时间周期
        interval = parse_interval(args.interval)
        
        # 解析交易所
        exchange = parse_exchange(args.symbol)
        
        # 从TX数据源获取数据（优先使用parquet缓存）
        print(f"正在获取{args.symbol}的{args.interval}K线数据...")
        print(f"数据源: TX (腾讯财经)")
        print(f"时间范围: 最近{args.days}天")
        
        bars = get_bar_data(
            symbol=args.symbol,
            exchange=exchange,
            interval=interval,
            days=args.days
        )
        
        if not bars:
            print("错误：未能获取到K线数据，请检查股票代码或网络连接", file=sys.stderr)
            sys.exit(1)
        
        print(f"成功获取{len(bars)}条K线数据")
        print(f"数据时间范围: {bars[0].datetime} 至 {bars[-1].datetime}")
        
        # 生成图表标题
        title = args.title
        if not title:
            title = f"{args.symbol} - {args.interval}K线图"
        
        # 绘制K线图表
        print("正在打开K线图表...")
        plot_bars(
            bars=bars,
            title=title,
            show_volume=not args.no_volume
        )
        
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
