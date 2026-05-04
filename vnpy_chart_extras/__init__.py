"""
VNPY 图表扩展模块
提供通用的K线图表展示功能
"""

from .bar_chart import (
    BarChart,
    show_bar_chart,
    run_bar_chart
)

__version__ = "0.1.0"
__all__ = [
    "BarChart",
    "show_bar_chart",
    "run_bar_chart"
]
