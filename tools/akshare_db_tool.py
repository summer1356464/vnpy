#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare行情数据保存工具 - CLI版本

命令行工具，用于将AKShare行情数据保存到VeighNa数据库系统

使用示例：
    # 保存实时行情（默认前100只）
    python akshare_db_tool.py spot
    
    # 保存指定数量的实时行情
    python akshare_db_tool.py spot --limit 50
    
    # 保存特定股票的历史数据
    python akshare_db_tool.py history --codes sh600519 sz000001
    
    # 保存特定时间范围的历史数据
    python akshare_db_tool.py history --codes sh600519 --start-date 20260101 --end-date 20260430
    
    # 保存所有功能
    python akshare_db_tool.py all
"""

import argparse
import sys
from datetime import datetime, timedelta
from vnpy.trader.database import get_database
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval, Exchange
import akshare as ak


class AkShareDatabaseTool:
    """AKShare行情数据保存工具"""
    
    def __init__(self):
        self.db = None
        self.initialize_database()
    
    def initialize_database(self):
        """初始化数据库连接"""
        try:
            self.db = get_database()
            print(f"✓ 数据库初始化成功: {self.db.__class__.__name__}")
            return True
        except Exception as e:
            print(f"✗ 数据库初始化失败: {e}")
            return False
    
    def save_spot_data(self, limit=100):
        """
        保存A股实时行情数据
        
        Args:
            limit: 保存的股票数量限制
        """
        if not self.db:
            if not self.initialize_database():
                return False
        
        print("\n" + "="*60)
        print("保存A股实时行情数据到数据库")
        print("="*60)
        
        try:
            # 获取A股实时行情数据
            print(f"\n1. 获取A股实时行情数据...")
            stock_zh_a_spot_df = ak.stock_zh_a_spot()
            print(f"  ✓ 实时行情数据获取成功: {len(stock_zh_a_spot_df)} 只股票")
            
            # 转换为BarData对象并保存到数据库
            print(f"\n2. 转换前 {limit} 只股票数据并保存到数据库...")
            
            # 选择要保存的股票数量
            sample_df = stock_zh_a_spot_df.head(limit)
            
            bars = []
            success_count = 0
            error_count = 0
            
            for index, row in sample_df.iterrows():
                try:
                    # 解析股票代码和交易所
                    code = str(row['代码'])
                    
                    # 确定交易所
                    if code.startswith('sh'):
                        exchange = Exchange.SSE
                        symbol = code[2:]
                    elif code.startswith('sz'):
                        exchange = Exchange.SZSE
                        symbol = code[2:]
                    elif code.startswith('bj'):
                        exchange = Exchange.BSE
                        symbol = code[2:]
                    else:
                        # 尝试从代码长度判断
                        if len(code) == 6:
                            if code.startswith(('6', '9')):
                                exchange = Exchange.SSE
                                symbol = code
                            elif code.startswith(('0', '2', '3')):
                                exchange = Exchange.SZSE
                                symbol = code
                            elif code.startswith('4'):
                                exchange = Exchange.BSE
                                symbol = code
                            else:
                                error_count += 1
                                continue
                        else:
                            error_count += 1
                            continue
                    
                    # 创建BarData对象
                    bar = BarData(
                        symbol=symbol,
                        exchange=exchange,
                        datetime=datetime.now(),
                        interval=Interval.DAILY,
                        volume=row.get('成交量', 0),
                        turnover=row.get('成交额', 0),
                        open_interest=0,
                        open_price=row.get('今开', 0),
                        high_price=row.get('最高', 0),
                        low_price=row.get('最低', 0),
                        close_price=row.get('最新价', 0),
                        gateway_name="AKSHARE"
                    )
                    bars.append(bar)
                    success_count += 1
                    
                    # 每处理20只股票显示进度
                    if (success_count + error_count) % 20 == 0:
                        print(f"  进度: {success_count + error_count}/{limit} 只股票")
                        
                except Exception as e:
                    print(f"  ⚠️  处理股票 {row['代码']} 时出错: {e}")
                    error_count += 1
                    continue
            
            print(f"  ✓ 数据转换完成: 成功 {success_count} 只, 失败 {error_count} 只")
            
            # 保存到数据库
            if bars:
                print(f"  ✓ 保存 {len(bars)} 条数据到数据库...")
                result = self.db.save_bar_data(bars)
                print(f"  ✓ 数据库保存结果: {result}")
            
            # 验证保存结果
            print("\n3. 验证数据库保存结果...")
            
            # 获取数据库概览
            overview = self.db.get_bar_overview()
            print(f"  ✓ 数据库中共有 {len(overview)} 种交易品种数据")
            
            # 显示最近保存的几个品种
            print("  最近保存的交易品种:")
            for item in overview[:5]:
                print(f"    {item.symbol}.{item.exchange} - {item.interval}: {item.count} 条数据")
            
            # 测试加载一条数据
            if bars:
                test_bar = bars[0]
                loaded_bars = self.db.load_bar_data(
                    symbol=test_bar.symbol,
                    exchange=test_bar.exchange,
                    interval=test_bar.interval,
                    start=datetime.now() - timedelta(days=1),
                    end=datetime.now() + timedelta(days=1)
                )
                print(f"  ✓ 验证加载: {test_bar.symbol}.{test_bar.exchange} 加载到 {len(loaded_bars)} 条数据")
            
            # 总结
            print("\n" + "="*60)
            print("实时行情数据保存任务完成")
            print("="*60)
            print(f"✓ 总共获取: {len(stock_zh_a_spot_df)} 只股票")
            print(f"✓ 成功保存: {success_count} 只股票到数据库")
            print(f"✓ 数据库类型: {self.db.__class__.__name__}")
            print(f"✓ 保存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ 实时行情保存任务失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_historical_data(self, codes=None, start_date=None, end_date=None, adjust="qfq"):
        """
        保存A股历史数据
        
        Args:
            codes: 股票代码列表（带交易所前缀，如sh600519）
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）
            adjust: 复权类型（qfq: 前复权, hfq: 后复权, '': 不复权）
        """
        if not self.db:
            if not self.initialize_database():
                return False
        
        print("\n" + "="*60)
        print("保存A股历史数据到数据库")
        print("="*60)
        
        try:
            # 默认股票列表
            if not codes:
                codes = ["sh600519", "sz000001", "sz000858"]
            
            # 默认时间范围（最近30天）
            today = datetime.today()
            if not start_date:
                start_date = (today - timedelta(days=30)).strftime("%Y%m%d")
            if not end_date:
                end_date = today.strftime("%Y%m%d")
            
            print(f"\n1. 历史数据参数设置:")
            print(f"  - 股票代码: {codes}")
            print(f"  - 时间范围: {start_date} 到 {end_date}")
            print(f"  - 复权类型: {adjust}")
            
            total_success = 0
            total_records = 0
            
            for stock_code in codes:
                print(f"\n2. 处理股票: {stock_code}")
                
                # 确定交易所
                if stock_code.startswith('sh'):
                    exchange = Exchange.SSE
                    symbol = stock_code[2:]
                elif stock_code.startswith('sz'):
                    exchange = Exchange.SZSE
                    symbol = stock_code[2:]
                elif stock_code.startswith('bj'):
                    exchange = Exchange.BSE
                    symbol = stock_code[2:]
                else:
                    print(f"  ⚠️  不支持的股票代码格式: {stock_code}")
                    continue
                
                # 获取历史数据
                try:
                    print(f"  ✓ 获取历史数据...")
                    hist_data = ak.stock_zh_a_hist_tx(
                        symbol=stock_code,
                        start_date=start_date,
                        end_date=end_date,
                        adjust=adjust
                    )
                    print(f"  ✓ 获取历史数据成功: {len(hist_data)} 条记录")
                    
                    # 转换为BarData对象
                    bars = []
                    for index, row in hist_data.iterrows():
                        # 处理不同类型的日期
                        dt = row['date']
                        
                        try:
                            # 尝试直接使用datetime对象
                            if hasattr(dt, 'strftime'):
                                # 已经是datetime或date对象
                                if not hasattr(dt, 'hour'):
                                    # 如果是date对象，转换为datetime对象
                                    dt = datetime.combine(dt, datetime.min.time())
                            else:
                                # 尝试转换为字符串再解析
                                dt_str = str(dt)
                                dt = datetime.strptime(dt_str, "%Y-%m-%d")
                        except Exception:
                            # 如果解析失败，跳过这条记录
                            continue
                        
                        bar = BarData(
                            symbol=symbol,  # 移除交易所前缀
                            exchange=exchange,
                            datetime=dt,
                            interval=Interval.DAILY,
                            volume=row.get('amount', 0),
                            turnover=row.get('amount', 0) * row.get('close', 0),
                            open_interest=0,
                            open_price=row.get('open', 0),
                            high_price=row.get('high', 0),
                            low_price=row.get('low', 0),
                            close_price=row.get('close', 0),
                            gateway_name="AKSHARE"
                        )
                        bars.append(bar)
                    
                    # 保存到数据库
                    if bars:
                        print(f"  ✓ 保存 {len(bars)} 条历史数据到数据库...")
                        result = self.db.save_bar_data(bars)
                        print(f"  ✓ 数据库保存结果: {result}")
                        total_success += 1
                        total_records += len(bars)
                        
                except Exception as e:
                    print(f"  ⚠️  保存 {stock_code} 历史数据时出错: {e}")
                    continue
            
            print("\n" + "="*60)
            print("历史数据保存任务完成")
            print("="*60)
            print(f"✓ 成功保存 {total_success}/{len(codes)} 只股票")
            print(f"✓ 总共保存 {total_records} 条历史数据")
            print(f"✓ 数据库类型: {self.db.__class__.__name__}")
            print(f"✓ 保存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ 历史数据保存任务失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_all_data(self, spot_limit=100, historical_codes=None, start_date=None, end_date=None):
        """
        保存所有类型的数据（实时行情+历史数据）
        
        Args:
            spot_limit: 实时行情保存数量限制
            historical_codes: 历史数据股票代码列表
            start_date: 历史数据开始日期
            end_date: 历史数据结束日期
        """
        print("\n" + "="*70)
        print("开始保存所有AKShare行情数据到数据库")
        print("="*70)
        
        # 保存实时行情
        spot_result = self.save_spot_data(limit=spot_limit)
        
        # 保存历史数据
        historical_result = self.save_historical_data(
            codes=historical_codes, 
            start_date=start_date, 
            end_date=end_date
        )
        
        print("\n" + "="*70)
        print("所有数据保存任务完成")
        print("="*70)
        print(f"✓ 实时行情保存: {'成功' if spot_result else '失败'}")
        print(f"✓ 历史数据保存: {'成功' if historical_result else '失败'}")
        print(f"✓ 总体结果: {'全部成功' if (spot_result and historical_result) else '部分失败'}")
        
        return spot_result and historical_result


def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(
        description="AKShare行情数据保存工具 - 将AKShare行情数据保存到VeighNa数据库系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
    # 保存实时行情（默认前100只）
    python akshare_db_tool.py spot
    
    # 保存指定数量的实时行情
    python akshare_db_tool.py spot --limit 50
    
    # 保存特定股票的历史数据
    python akshare_db_tool.py history --codes sh600519 sz000001
    
    # 保存特定时间范围的历史数据
    python akshare_db_tool.py history --codes sh600519 --start-date 20260101 --end-date 20260430
    
    # 保存所有功能
    python akshare_db_tool.py all
        """)
    
    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # spot命令 - 保存实时行情
    spot_parser = subparsers.add_parser("spot", help="保存A股实时行情数据")
    spot_parser.add_argument(
        "--limit", 
        type=int, 
        default=100, 
        help="保存的股票数量限制 (默认: 100)"
    )
    
    # history命令 - 保存历史数据
    history_parser = subparsers.add_parser("history", help="保存A股历史数据")
    history_parser.add_argument(
        "--codes", 
        nargs="*", 
        help="股票代码列表（带交易所前缀，如sh600519）"
    )
    history_parser.add_argument(
        "--start-date", 
        type=str, 
        help="开始日期（格式：YYYYMMDD）"
    )
    history_parser.add_argument(
        "--end-date", 
        type=str, 
        help="结束日期（格式：YYYYMMDD）"
    )
    history_parser.add_argument(
        "--adjust", 
        type=str, 
        choices=["qfq", "hfq", ""],
        default="qfq", 
        help="复权类型 (默认: qfq)"
    )
    
    # all命令 - 保存所有数据
    all_parser = subparsers.add_parser("all", help="保存所有类型的数据（实时行情+历史数据）")
    all_parser.add_argument(
        "--spot-limit", 
        type=int, 
        default=100, 
        help="实时行情保存数量限制 (默认: 100)"
    )
    all_parser.add_argument(
        "--historical-codes", 
        nargs="*", 
        help="历史数据股票代码列表"
    )
    all_parser.add_argument(
        "--start-date", 
        type=str, 
        help="历史数据开始日期（格式：YYYYMMDD）"
    )
    all_parser.add_argument(
        "--end-date", 
        type=str, 
        help="历史数据结束日期（格式：YYYYMMDD）"
    )
    
    # 解析参数
    args = parser.parse_args()
    
    # 创建工具实例
    tool = AkShareDatabaseTool()
    
    # 根据命令执行相应功能
    if args.command == "spot":
        result = tool.save_spot_data(limit=args.limit)
        sys.exit(0 if result else 1)
    
    elif args.command == "history":
        result = tool.save_historical_data(
            codes=args.codes,
            start_date=args.start_date,
            end_date=args.end_date,
            adjust=args.adjust
        )
        sys.exit(0 if result else 1)
    
    elif args.command == "all":
        result = tool.save_all_data(
            spot_limit=args.spot_limit,
            historical_codes=args.historical_codes,
            start_date=args.start_date,
            end_date=args.end_date
        )
        sys.exit(0 if result else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
