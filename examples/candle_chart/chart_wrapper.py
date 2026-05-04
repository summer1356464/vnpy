"""
通用K线图表展示模块，封装了VNPY的ChartWidget，便于快速展示K线数据
"""
from datetime import datetime
from typing import List, Optional
from vnpy.trader.ui import create_qapp, QtCore
from vnpy.trader.object import BarData
from vnpy.chart import ChartWidget, VolumeItem, CandleItem


class BarChartWrapper:
    """
    K线图表封装类，提供简洁的API来展示K线数据
    """
    
    def __init__(self, 
                 title: str = "K线图表", 
                 show_volume: bool = True):
        """
        初始化K线图表
        
        Args:
            title: 图表窗口标题
            show_volume: 是否显示成交量
        """
        self.title = title
        self.show_volume = show_volume
        
        # 创建Qt应用
        self.app = create_qapp()
        
        # 创建图表控件
        self.widget = ChartWidget()
        self.widget.setWindowTitle(title)
        
        # 配置图表
        self._setup_chart()
    
    def _setup_chart(self):
        """配置图表的基本结构"""
        # 添加蜡烛图子图
        self.widget.add_plot("candle", hide_x_axis=True)
        
        # 添加成交量子图
        if self.show_volume:
            self.widget.add_plot("volume", maximum_height=200)
        
        # 添加蜡烛图项目
        self.widget.add_item(CandleItem, "candle", "candle")
        
        # 添加成交量项目
        if self.show_volume:
            self.widget.add_item(VolumeItem, "volume", "volume")
        
        # 添加交互光标
        self.widget.add_cursor()
    
    def show_bars(self, bars: List[BarData]):
        """
        显示K线数据
        
        Args:
            bars: BarData对象列表，需按时间顺序排列
        """
        if not bars:
            raise ValueError("K线数据不能为空")
        
        # 更新历史数据
        self.widget.update_history(bars)
    
    def add_bar(self, bar: BarData):
        """
        添加单根K线（用于动态更新）
        
        Args:
            bar: 新的BarData对象
        """
        self.widget.update_bar(bar)
    
    def start_dynamic_update(self, update_func, interval_ms: int = 100):
        """
        启动动态更新
        
        Args:
            update_func: 回调函数，返回新的BarData对象
            interval_ms: 更新间隔（毫秒）
        """
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(lambda: self._on_update(update_func))
        self.timer.start(interval_ms)
    
    def _on_update(self, update_func):
        """
        定时更新回调
        """
        try:
            bar = update_func()
            if bar:
                self.add_bar(bar)
        except Exception as e:
            print(f"动态更新出错: {e}")
    
    def show(self):
        """显示图表窗口"""
        self.widget.show()
    
    def run(self):
        """
        运行图表应用（阻塞直到窗口关闭）
        """
        self.show()
        self.app.exec()


def plot_bars(bars: List[BarData], 
              title: str = "K线图表", 
              show_volume: bool = True):
    """
    快速绘制K线图表的便捷函数
    
    Args:
        bars: BarData对象列表
        title: 图表标题
        show_volume: 是否显示成交量
    """
    chart = BarChartWrapper(title=title, show_volume=show_volume)
    chart.show_bars(bars)
    chart.run()


def create_chart(title: str = "K线图表", 
                 show_volume: bool = True) -> BarChartWrapper:
    """
    创建K线图表实例
    
    Args:
        title: 图表标题
        show_volume: 是否显示成交量
        
    Returns:
        BarChartWrapper实例
    """
    return BarChartWrapper(title=title, show_volume=show_volume)
