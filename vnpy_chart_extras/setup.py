from setuptools import setup, find_packages

setup(
    name="vnpy_chart_extras",
    version="0.1.0",
    description="VNPY图表扩展模块，提供通用K线图表展示功能",
    long_description="""VNPY图表扩展模块

提供简洁易用的K线图表展示功能，支持：
- 快速展示历史K线数据
- 实时更新K线图表
- 自定义图表配置
- 支持显示/隐藏成交量

使用示例：
```python
from vnpy_chart_extras import run_bar_chart
from vnpy.trader.object import BarData

# 准备BarData数据列表
bars = [...]  # 你的K线数据

# 快速展示K线图表
run_bar_chart(bars, title="我的K线图表")
```
""",
    long_description_content_type="text/markdown",
    author="VNPY Team",
    author_email="",
    url="https://github.com/vnpy/vnpy",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "vnpy>=3.0.0",
        "PyQt5>=5.15.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "black>=22.0.0",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires='>=3.8',
)
