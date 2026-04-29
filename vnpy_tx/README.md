# vnpy-tx

基于腾讯财经API的vn.py行情数据源模块，使用AKShare库获取A股历史数据。

## 功能特点

- 支持查询A股历史K线数据
- 自动计算成交量
- 支持前复权数据
- 兼容vn.py的数据feed接口
- 支持数据缓存功能

## 安装方法

1. 安装vn.py框架
```bash
pip install vnpy
```

2. 安装vnpy-tx模块
```bash
# 从源代码安装
cd vnpy_tx
pip install .
```

3. 安装依赖包
```bash
pip install akshare pandas numpy
```

## 配置使用

1. 在vn.py的全局配置文件中设置数据feed：
```json
{
    "datafeed.name": "tx",
    "datafeed.use_cache": true
}
```

2. 在代码中使用：
```python
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime

# 获取数据feed实例
datafeed = get_datafeed()

# 查询历史数据
req = HistoryRequest(
    symbol="600000",
    exchange=Exchange.SSE,
    interval=Interval.DAILY,
    start=datetime(2023, 1, 1),
    end=datetime(2023, 12, 31)
)

bars = datafeed.query_bar_history(req)
print(f"获取到{len(bars)}条K线数据")
```

## 注意事项

1. 腾讯财经API不提供历史Tick数据，因此`query_tick_history`方法返回空列表
2. 成交量是根据成交额和收盘价计算得出的估算值
3. 建议开启数据缓存功能，以提高查询效率并减少网络请求
4. 使用过程中如遇到数据获取失败，请检查网络连接或尝试调整查询时间范围

## 支持的交易所

- 上海证券交易所（SSE）
- 深圳证券交易所（SZSE）

## 支持的时间周期

- 日线（DAILY）

## 更新日志

### v0.1.0 (2026-04-29)
- 初始版本发布
- 支持查询A股历史K线数据
- 兼容vn.py 3.0.0+

## 许可证

MIT License