from datetime import datetime
from typing import List, Optional
from vnpy.trader.ui import create_qapp, QtCore
from vnpy.trader.object import BarData
from vnpy.chart import ChartWidget, VolumeItem, CandleItem


class BarChart:
    """
    通用K线图表展示模块，用于可视化BarData数据
    """
    
    def __init__(self, 
                 title: str = "K线图表", 
                 show_volume: bool = True, 
                 real_time_update: bool = False, 
                 update_interval: int = 100):
        """
        初始化K线图表
        
        Args:
            title: 图表标题
            show_volume: 是否显示成交量
            real_time_update: 是否支持实时更新
            update_interval: 实时更新间隔（毫秒）
        """
        self.title = title
        self.show_volume = show_volume
        self.real_time_update = real_time_update
        self.update_interval = update_interval
        
        # 创建Qt应用
        self.app = create_qapp()
        
        # 创建图表控件
        self.widget = ChartWidget()
        self.widget.setWindowTitle(title)
        
        # 配置图表
        self._init_chart()
        
        # 实时更新相关
        self.timer = None
        self.update_callback = None
        
        # 数据缓存
        self.bars: List[BarData] = []
    
    def _init_chart(self):
        """初始化图表配置"""
        # 添加蜡烛图子图
        self.widget.add_plot("candle", hide_x_axis=True)
        
        # 添加成交量子图（如果需要）
        if self.show_volume:
            self.widget.add_plot("volume", maximum_height=200)
        
        # 添加蜡烛图项目
        self.widget.add_item(CandleItem, "candle", "candle")
        
        # 添加成交量项目（如果需要）
        if self.show_volume:
            self.widget.add_item(VolumeItem, "volume", "volume")
        
        # 添加交互光标
        self.widget.add_cursor()
    
    def set_bar_data(self, bars: List[BarData]):
        """
        设置K线数据
        
        Args:
            bars: BarData对象列表，需要按时间顺序排列
        """
        if not bars:
            raise ValueError("K线数据不能为空")
        
        self.bars = bars
        
        # 更新历史数据
        self.widget.update_history(bars)
    
    def add_bar(self, bar: BarData):
        """
        添加单根K线（用于实时更新）
        
        Args:
            bar: 新的BarData对象
        """
        self.bars.append(bar)
        self.widget.update_bar(bar)
    
    def set_real_time_callback(self, callback):
        """
        设置实时更新回调函数
        
        Args:
            callback: 无参数函数，返回新的BarData对象
        """
        self.update_callback = callback
    
    def start_real_time_update(self):
        """启动实时更新"""
        if not self.real_time_update:
            raise RuntimeError("未启用实时更新功能")
        
        if not self.update_callback:
            raise RuntimeError("未设置实时更新回调函数")
        
        if self.timer is None:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self._on_timer)
            self.timer.start(self.update_interval)
    
    def stop_real_time_update(self):
        """停止实时更新"""
        if self.timer:
            self.timer.stop()
            self.timer = None
    
    def _on_timer(self):
        """定时器回调函数"""
        try:
            if self.update_callback:
                bar = self.update_callback()
                if bar:
                    self.add_bar(bar)
        except Exception as e:
            print(f"实时更新出错: {e}")
    
    def show(self):
        """显示图表"""
        self.widget.show()
    
    def run(self):
        """运行应用程序，阻塞直到窗口关闭"""
        self.show()
        self.app.exec()


def show_bar_chart(bars: List[BarData], 
                   title: str = "K线图表", 
                   show_volume: bool = True) -> BarChart:
    """
    快速显示K线图表的便捷函数
    
    Args:
        bars: BarData对象列表
        title: 图表标题
        show_volume: 是否显示成交量
        
    Returns:
        BarChart对象
    """
    chart = BarChart(title=title, show_volume=show_volume)
    chart.set_bar_data(bars)
    chart.show()
    return chart


def run_bar_chart(bars: List[BarData], 
                  title: str = "K线图表", 
                  show_volume: bool = True):
    """
    快速运行K线图表应用程序
    
    Args:
        bars: BarData对象列表
        title: 图表标题
        show_volume: 是否显示成交量
    """
    chart = BarChart(title=title, show_volume=show_volume)
    chart.set_bar_data(bars)
    chart.run()
