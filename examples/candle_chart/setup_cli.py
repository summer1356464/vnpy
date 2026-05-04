"""
K线图表CLI工具安装脚本
"""
from setuptools import setup, find_packages

setup(
    name="vnpy-chart-cli",
    version="0.1.0",
    description="VNPY K线图表命令行工具",
    long_description="""
VNPY K线图表命令行工具

一个简单的命令行工具，用于快速查看股票K线图表。

使用示例：
    vnpy-chart 000001          # 查看上证指数日线图
    vnpy-chart 600519 -i 1h    # 查看贵州茅台小时线图
    vnpy-chart IF888 -d 180    # 查看沪深300指数期货180天数据
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
    entry_points={
        "console_scripts": [
            "vnpy-chart=chart_cli:main",
        ],
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
