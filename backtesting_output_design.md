# 回测模块输出设计文档

## 1. 概述

VNPY的回测模块提供了完整的量化策略回测功能，包括数据加载、策略执行、订单匹配、盈亏计算和结果分析等。本文档主要描述回测模块的输出设计，包括日志输出、数据结构输出、可视化输出等。

## 2. 核心输出组件

### 2.1 回测引擎 (BacktestingEngine)

回测引擎是回测模块的核心组件，负责管理回测流程并生成输出结果。主要输出功能包括：

- 日志输出
- 数据结构输出
- 可视化输出
- 交易和订单数据输出

### 2.2 输出数据结构

回测模块使用多种数据结构来存储和输出回测结果：

| 数据结构 | 类型 | 描述 |
|---------|------|------|
| daily_df | polars.DataFrame | 每日回测结果数据 |
| statistics | dict | 策略统计指标 |
| trades | dict[str, TradeData] | 交易记录 |
| limit_orders | dict[str, OrderData] | 订单记录 |
| daily_results | dict[date, PortfolioDailyResult] | 每日盈亏结果 |

## 3. 日志输出

回测引擎通过内置的logger输出回测过程和结果的关键信息，包括：

- 数据加载状态
- 策略初始化信息
- 回测执行进度
- 异常信息
- 策略统计指标

### 日志示例

```
开始加载历史数据
所有历史数据加载完成
策略初始化完成
开始回放历史数据
历史数据回放结束
开始计算逐日盯市盈亏
逐日盯市盈亏计算完成
开始计算策略统计指标
------------------------------
首个交易日：  2023-01-03
最后交易日：  2023-12-29
总交易日：  243
盈利交易日：  128
亏损交易日：  115
起始资金：  1,000,000.00
结束资金：  1,234,567.89
总收益率：  23.46%
年化收益：  23.46%
最大回撤:   -123,456.78
百分比最大回撤: -12.35%
最长回撤天数:   67
总盈亏：  234,567.89
总手续费：  12,345.67
总成交金额：  123,456,789.00
总成交笔数：  567
日均盈亏：  965.30
日均手续费：  50.80
日均成交金额：  508,052.63
日均成交笔数：  2.33
日均收益率：  0.08%
收益标准差：  1.23%
Sharpe Ratio：  1.89
收益回撤比：  1.90
策略统计指标计算完成
```

## 4. 数据结构输出

### 4.1 每日回测结果 (daily_df)

`daily_df` 是一个 polars DataFrame，包含每日回测结果的详细数据：

| 列名 | 类型 | 描述 |
|------|------|------|
| date | Date | 日期 |
| trade_count | Int64 | 当日成交笔数 |
| turnover | Float64 | 当日成交金额 |
| commission | Float64 | 当日手续费 |
| trading_pnl | Float64 | 当日交易盈亏 |
| holding_pnl | Float64 | 当日持仓盈亏 |
| total_pnl | Float64 | 当日总盈亏 |
| net_pnl | Float64 | 当日净盈亏 (总盈亏 - 手续费) |
| balance | Float64 | 当日资金余额 |
| return | Float64 | 当日收益率 |
| highlevel | Float64 | 资金余额的历史最高值 |
| drawdown | Float64 | 当日资金回撤 |
| ddpercent | Float64 | 当日资金回撤百分比 |

### 4.2 策略统计指标 (statistics)

`statistics` 是一个字典，包含策略的主要统计指标：

| 键名 | 类型 | 描述 |
|------|------|------|
| start_date | str | 首个交易日 |
| end_date | str | 最后交易日 |
| total_days | int | 总交易日数 |
| profit_days | int | 盈利交易日数 |
| loss_days | int | 亏损交易日数 |
| capital | float | 起始资金 |
| end_balance | float | 结束资金 |
| max_drawdown | float | 最大资金回撤 |
| max_ddpercent | float | 最大回撤百分比 |
| max_drawdown_duration | int | 最长回撤天数 |
| total_net_pnl | float | 总净盈亏 |
| daily_net_pnl | float | 日均净盈亏 |
| total_commission | float | 总手续费 |
| daily_commission | float | 日均手续费 |
| total_turnover | float | 总成交金额 |
| daily_turnover | float | 日均成交金额 |
| total_trade_count | int | 总成交笔数 |
| daily_trade_count | float | 日均成交笔数 |
| total_return | float | 总收益率 |
| annual_return | float | 年化收益率 |
| daily_return | float | 日均收益率 |
| return_std | float | 收益率标准差 |
| sharpe_ratio | float | 夏普比率 |
| return_drawdown_ratio | float | 收益回撤比 |

## 5. 可视化输出

回测模块提供了两种可视化输出功能，使用 plotly 库生成交互式图表：

### 5.1 回测结果图表 (show_chart)

`show_chart()` 方法生成包含四个子图的回测结果图表：

1. **资金曲线 (Balance)**：显示策略资金余额随时间的变化
2. **资金回撤 (Drawdown)**：显示策略资金回撤随时间的变化
3. **每日盈亏 (Daily Pnl)**：显示策略每日净盈亏的柱状图
4. **盈亏分布 (Pnl Distribution)**：显示策略每日净盈亏的直方图

### 5.2 策略绩效对比图表 (show_performance)

`show_performance(benchmark_symbol)` 方法生成包含五个子图的策略绩效对比图表：

1. **收益率对比 (Return)**：显示策略收益率与基准收益率的对比
2. **超额收益 (Alpha)**：显示策略相对于基准的超额收益
3. **换手率 (Turnover)**：显示策略换手率随时间的变化
4. **超额收益回撤 (Alpha Drawdown)**：显示策略超额收益的回撤
5. **考虑成本的超额收益回撤 (Alpha Drawdown with Cost)**：显示考虑交易成本后的超额收益回撤

## 6. 交易和订单数据输出

### 6.1 获取所有交易记录 (get_all_trades)

`get_all_trades()` 方法返回所有交易记录的列表，每个交易记录是一个 `TradeData` 对象，包含：

- 交易ID
- 合约信息
- 交易方向
- 开平仓类型
- 交易价格
- 交易数量
- 交易时间
- 手续费

### 6.2 获取所有订单记录 (get_all_orders)

`get_all_orders()` 方法返回所有订单记录的列表，每个订单记录是一个 `OrderData` 对象，包含：

- 订单ID
- 合约信息
- 订单方向
- 开平仓类型
- 订单价格
- 订单数量
- 成交数量
- 订单状态
- 订单时间

### 6.3 获取所有每日盈亏结果 (get_all_daily_results)

`get_all_daily_results()` 方法返回所有每日盈亏结果的列表，每个每日盈亏结果是一个 `PortfolioDailyResult` 对象，包含：

- 日期
- 收盘价格
- 成交笔数
- 成交金额
- 手续费
- 交易盈亏
- 持仓盈亏
- 总盈亏
- 净盈亏
- 各合约的每日盈亏结果

## 7. 输出流程

回测模块的输出流程如下：

1. **初始化回测**：设置回测参数，加载历史数据
2. **执行回测**：回放历史数据，执行策略逻辑
3. **计算逐日盈亏**：计算每日的盈亏情况，生成 `daily_df`
4. **计算统计指标**：基于 `daily_df` 计算策略统计指标，生成 `statistics`
5. **输出结果**：
   - 打印策略统计指标日志
   - 生成可视化图表 (可选)
   - 返回 `daily_df` 和 `statistics` (可选)
   - 提供获取交易和订单数据的接口

## 8. 代码示例

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.strategy.backtesting import BacktestingEngine
from vnpy.alpha.strategy.strategies.equity_demo_strategy import EquityDemoStrategy
from datetime import datetime

# 创建AlphaLab实例
lab = AlphaLab("../lab")

# 创建回测引擎
engine = BacktestingEngine(lab)

# 设置回测参数
engine.set_parameters(
    vt_symbols=["000001.SZ", "600000.SH"],
    interval=Interval.DAILY,
    start=datetime(2023, 1, 1),
    end=datetime(2023, 12, 31),
    capital=1000000
)

# 添加策略
engine.add_strategy(EquityDemoStrategy, {}, signal_df)

# 加载数据
engine.load_data()

# 执行回测
engine.run_backtesting()

# 计算回测结果
daily_df = engine.calculate_result()

# 计算统计指标
statistics = engine.calculate_statistics()

# 显示回测结果图表
engine.show_chart()

# 显示策略绩效对比图表
engine.show_performance("000300.SH")

# 获取交易记录
trades = engine.get_all_trades()

# 获取订单记录
orders = engine.get_all_orders()
```

## 9. 总结

VNPY的回测模块提供了丰富的输出功能，包括：

- **日志输出**：实时反馈回测过程和结果
- **数据结构输出**：提供结构化的回测结果数据，方便后续分析和处理
- **可视化输出**：生成直观的图表，帮助用户理解策略表现
- **交易和订单数据输出**：提供详细的交易和订单记录，方便用户进行深入分析

这些输出功能使得用户能够全面了解策略的表现，并进行深入的分析和优化。