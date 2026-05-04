# vnpy_chart_extras

VNPY图表扩展模块，提供通用的K线图表展示功能。

## 功能特点

- 快速展示历史K线数据
- 支持实时更新K线图表
- 自定义图表配置
- 支持显示/隐藏成交量
- 简洁易用的API接口

## 安装

### 从源码安装

```bash
cd vnpy_chart_extras
pip install -e .
```

## 使用示例

### 快速展示K线图表

```python
from datetime import datetime, timedelta
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_chart_extras import run_bar_chart

# 生成示例K线数据
bars = []
start_datetime = datetime(2023, 1, 1)
base_price = 4000.0

for i in range(1000):
    dt = start_datetime + timedelta(minutes=i)
    
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

# 快速展示K线图表
run_bar_chart(bars, title="我的K线图表")
```

### 使用类接口创建K线图表

```python
from vnpy_chart_extras import BarChart

# 创建图表实例
chart = BarChart(title="类接口K线图表", show_volume=True)

# 设置数据
chart.set_bar_data(bars)

# 显示图表
chart.run()
```

### 实时更新K线图表

```python
from vnpy_chart_extras import BarChart

# 创建支持实时更新的图表
chart = BarChart(
    title="实时更新K线图表",
    show_volume=True,
    real_time_update=True,
    update_interval=200  # 每200毫秒更新一次
)

# 设置初始数据
chart.set_bar_data(initial_bars)

# 定义实时数据生成函数
def generate_new_bar():
    # 生成新的BarData对象
    # ...
    return new_bar

# 设置实时更新回调
chart.set_real_time_callback(generate_new_bar)

# 启动实时更新
chart.start_real_time_update()

# 显示图表
chart.run()
```

## API 文档

### BarChart 类

#### 初始化参数

- `title`: 图表标题，默认为 "K线图表"
- `show_volume`: 是否显示成交量，默认为 True
- `real_time_update`: 是否支持实时更新，默认为 False
- `update_interval`: 实时更新间隔（毫秒），默认为 100

#### 主要方法

- `set_bar_data(bars)`: 设置K线数据
- `add_bar(bar)`: 添加单根K线（用于实时更新）
- `set_real_time_callback(callback)`: 设置实时更新回调函数
- `start_real_time_update()`: 启动实时更新
- `stop_real_time_update()`: 停止实时更新
- `show()`: 显示图表
- `run()`: 运行应用程序，阻塞直到窗口关闭

### 便捷函数

- `show_bar_chart(bars, title, show_volume)`: 快速显示K线图表，返回BarChart对象
- `run_bar_chart(bars, title, show_volume)`: 快速运行K线图表应用程序

## 依赖

- vnpy >= 3.0.0
- PyQt5 >= 5.15.0

## 许可证

MIT License
