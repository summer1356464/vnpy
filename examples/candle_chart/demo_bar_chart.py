from datetime import datetime, timedelta
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_chart_extras import BarChart, show_bar_chart, run_bar_chart


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


def demo_quick_start():
    """演示快速启动方式"""
    print("演示1: 快速运行K线图表")
    bars = generate_sample_data(500)
    run_bar_chart(bars, title="快速K线图表示例")


def demo_class_interface():
    """演示类接口使用"""
    print("演示2: 使用类接口创建K线图表")
    bars = generate_sample_data(800)
    
    # 创建图表实例
    chart = BarChart(title="类接口K线图表", show_volume=True)
    
    # 设置数据
    chart.set_bar_data(bars)
    
    # 显示图表
    chart.run()


def demo_real_time_update():
    """演示实时更新功能"""
    print("演示3: 实时更新K线图表")
    
    # 初始数据
    initial_bars = generate_sample_data(500)
    
    # 创建支持实时更新的图表
    chart = BarChart(
        title="实时更新K线图表",
        show_volume=True,
        real_time_update=True,
        update_interval=200  # 每200毫秒更新一次
    )
    
    # 设置初始数据
    chart.set_bar_data(initial_bars)
    
    # 准备实时数据生成
    last_bar = initial_bars[-1]
    bar_counter = 500
    
    def generate_new_bar():
        """生成新的K线数据"""
        nonlocal last_bar, bar_counter
        
        # 创建新的时间
        new_dt = last_bar.datetime + timedelta(minutes=1)
        bar_counter += 1
        
        # 生成价格（基于前一根K线的收盘价）
        base_price = last_bar.close_price
        open_price = base_price + (bar_counter % 5) * 0.1
        high_price = open_price + 1.0 + (bar_counter % 3)
        low_price = open_price - 0.5 - (bar_counter % 2)
        close_price = low_price + (high_price - low_price) * 0.6 + (bar_counter % 4) * 0.1
        
        # 创建新的BarData对象
        new_bar = BarData(
            symbol="IF888",
            exchange=Exchange.CFFEX,
            datetime=new_dt,
            interval=Interval.MINUTE,
            volume=bar_counter * 100,
            turnover=close_price * bar_counter * 100,
            open_interest=100000 + bar_counter * 100,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            gateway_name="REAL_TIME"
        )
        
        # 更新最后一根K线
        last_bar = new_bar
        
        return new_bar
    
    # 设置实时更新回调
    chart.set_real_time_callback(generate_new_bar)
    
    # 启动实时更新
    chart.start_real_time_update()
    
    # 显示图表
    chart.run()


def demo_no_volume():
    """演示不显示成交量的情况"""
    print("演示4: 不显示成交量的K线图表")
    bars = generate_sample_data(600)
    run_bar_chart(bars, title="无成交量K线图表", show_volume=False)


if __name__ == "__main__":
    # 选择要运行的演示
    print("请选择要运行的演示:")
    print("1. 快速启动K线图表")
    print("2. 使用类接口创建K线图表")
    print("3. 实时更新K线图表")
    print("4. 不显示成交量的K线图表")
    
    choice = input("请输入演示编号 (1-4): ").strip()
    
    if choice == "1":
        demo_quick_start()
    elif choice == "2":
        demo_class_interface()
    elif choice == "3":
        demo_real_time_update()
    elif choice == "4":
        demo_no_volume()
    else:
        print("无效的选择，运行默认演示")
        demo_quick_start()
