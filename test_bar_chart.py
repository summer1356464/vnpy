import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath("."))

from datetime import datetime, timedelta
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_chart_extras.bar_chart import BarChart, show_bar_chart, run_bar_chart


def generate_sample_data(count: int = 1000) -> list[BarData]:
    """生成示例K线数据"""
    bars = []
    start_datetime = datetime(2023, 1, 1)
    base_price = 4000.0
    
    for i in range(count):
        dt = start_datetime + timedelta(minutes=i)
        
        # 生成模拟价格数据
        open_price = base_price + (i * 0.5) + (i % 10)
        high_price = open_price + 2.0 + (i % 5)
        low_price = open_price - 1.0 - (i % 3)
        close_price = low_price + (high_price - low_price) * 0.7 + (i % 4)
        
        bar = BarData(
            symbol="IF888",
            exchange=Exchange.CFFEX,
            datetime=dt,
            interval=Interval.MINUTE,
            volume=i * 100,
            turnover=close_price * i * 100,
            open_interest=100000 + i * 100,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            gateway_name="SAMPLE"
        )
        bars.append(bar)
    
    return bars


if __name__ == "__main__":
    print("正在生成示例数据...")
    bars = generate_sample_data(500)
    print(f"生成了{len(bars)}条K线数据")
    
    print("正在显示K线图表...")
    
    # 测试run_bar_chart函数
    try:
        run_bar_chart(bars, title="测试K线图表")
        print("K线图表显示成功!")
    except Exception as e:
        print(f"K线图表显示出错: {e}")
