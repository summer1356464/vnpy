# VeighNa 项目设计文档索引

## 重要提醒

**分析和修改活动进行之前，先看下项目设计文档；如果没有，就先进行项目分析，并记录到设计文档；**

## 设计文档位置

本项目的设计文档统一存放在以下目录：

```
docs/
└── design/
    ├── design_doc.md              # 系统主设计文档
    ├── backtesting_output_design.md  # 回测模块输出设计
    └── cached_datafeed_design.md     # 数据缓存系统设计
```

## 设计文档概览

### 1. 系统主设计文档 (design_doc.md)

**文件路径**: `docs/design/design_doc.md`

**主要内容**:
- 项目概述和功能亮点
- 目录结构和模块职责
- 系统架构和主流程
- 核心功能模块详解
- 核心 API/类/函数说明
- 技术栈与依赖列表
- 配置、部署与开发指南
- 监控与维护建议

### 2. 回测模块输出设计文档 (backtesting_output_design.md)

**文件路径**: `docs/design/backtesting_output_design.md`

**主要内容**:
- 回测引擎核心组件说明
- 输出数据结构定义
- 日志输出格式和示例
- 可视化输出功能
- 交易和订单数据输出接口
- 回测执行流程

### 3. 数据缓存系统设计文档 (cached_datafeed_design.md)

**文件路径**: `docs/design/cached_datafeed_design.md`

**主要内容**:
- 缓存系统架构设计
- 核心类和接口定义
- 数据查询流程
- 缓存策略和优化
- 配置与使用指南
- 扩展与维护建议

### 4. AlphaLab 投研缓存系统

**核心文件**: `vnpy/alpha/lab.py`

**主要内容**:
- **Parquet 文件缓存**：使用 Polars 库实现高效的 K 线数据读写
- **目录结构**：
  - `daily/` - 日线数据缓存（`.parquet` 格式）
  - `minute/` - 分钟线数据缓存（`.parquet` 格式）
  - `component/` - 指数成分股数据（shelve 格式）
  - `dataset/` - 因子数据集（pickle 格式）
  - `model/` - 预测模型（pickle 格式）
  - `signal/` - 信号数据（`.parquet` 格式）
- **核心方法**：
  - `save_bar_data()` - 保存 K 线数据到 Parquet 文件
  - `load_bar_data()` - 从 Parquet 文件加载 K 线数据
  - `load_bar_df()` - 批量加载多股票数据为 DataFrame
  - `save_component_data()` - 保存指数成分股信息
  - `load_component_data()` - 加载指数成分股信息
- **数据格式**：
  - 时间精度：纳秒级（`pl.Datetime(time_unit="ns")`）
  - 数值类型：Float64 统一类型
  - 支持字段：datetime, open, high, low, close, volume, turnover, open_interest
- **缓存特性**：
  - 自动去重：基于 datetime 字段去重
  - 自动合并：新数据与已有数据合并
  - 数据标准化：价格按首日收盘价归一化
  - 停牌处理：成交量为 0 的行转换为 NaN

## 设计文档使用规范

### 1. 分析活动前

在进行任何代码分析活动之前，请：
1. 阅读相关的设计文档
2. 理解系统架构和模块职责
3. 了解核心类和 API 的设计意图

### 2. 修改活动前

在进行任何代码修改活动之前，请：
1. 阅读相关的设计文档
2. 确认修改符合系统设计规范
3. 评估修改对其他模块的影响
4. 如果设计文档中没有相关内容，先进行项目分析

### 3. 新功能开发前

在进行新功能开发之前，请：
1. 检查是否已有相关设计文档
2. 如果没有，先编写设计文档
3. 确保设计文档涵盖：
   - 功能需求分析
   - 架构设计
   - API 设计
   - 数据结构设计
   - 与其他模块的交互

### 4. 设计文档更新

在完成代码修改后，请：
1. 同步更新相关的设计文档
2. 确保文档内容与代码实现一致
3. 记录重要的设计决策和技术选型

## 项目结构速览

```
vnpy/                              # 核心代码目录
├── alpha/                         # AI量化模块
│   ├── dataset/                   # 因子特征工程
│   ├── model/                     # 预测模型训练
│   ├── strategy/                  # 策略投研开发
│   └── lab.py                     # AlphaLab 投研实验室（Parquet缓存核心）
├── chart/                         # K线图表模块
├── event/                         # 事件驱动引擎
├── rpc/                           # 跨进程通信模块
└── trader/                        # 交易核心模块
    ├── ui/                        # 用户界面组件
    ├── cached_datafeed.py         # 数据服务缓存
    ├── enhanced_cached_datafeed.py # 增强版缓存数据服务
    └── stock_metadata.py          # 股票元信息管理

docs/                              # 文档目录
├── community/                     # 社区文档
├── elite/                         # 精英版文档
└── design/                        # 设计文档（本目录）

examples/                          # 示例代码
tests/                             # 测试代码
strategies/                        # 策略实现
tools/                             # 工具脚本
```

## AlphaLab 缓存目录结构

```
lab_path/                          # AlphaLab 数据根目录
├── daily/                         # 日线数据缓存
│   └── {vt_symbol}.parquet        # 单股票日线数据
├── minute/                        # 分钟线数据缓存
│   └── {vt_symbol}.parquet        # 单股票分钟线数据
├── component/                     # 指数成分股数据
│   └── {index_symbol}             # shelve 格式存储
├── dataset/                       # 因子数据集
│   └── {name}.pkl                 # pickle 格式
├── model/                         # 预测模型
│   └── {name}.pkl                 # pickle 格式
├── signal/                        # 信号数据
│   └── {name}.parquet             # parquet 格式
└── contract.json                  # 合约配置信息
```

## 核心模块入口

| 模块 | 核心文件 | 主要职责 |
|------|----------|----------|
| 交易核心 | vnpy/trader/engine.py | 订单管理、账户管理、事件处理 |
| AI量化/投研 | vnpy/alpha/lab.py | AlphaLab 投研实验室（Parquet 文件缓存核心） |
| 回测引擎 | vnpy/alpha/strategy/backtesting.py | 策略回测 |
| 事件引擎 | vnpy/event/engine.py | 事件分发和处理 |
| 数据缓存 | vnpy/trader/cached_datafeed.py | 数据服务缓存 |
| 增强缓存 | vnpy/trader/enhanced_cached_datafeed.py | 增强版缓存数据服务（上市/退市时间检查） |
| 元信息管理 | vnpy/trader/stock_metadata.py | 股票元信息管理（上市/退市时间、缓存状态） |

## 双缓存架构说明

VeighNa 采用**双缓存架构**，分别服务于不同的数据使用场景：

### 1. DataFeed 缓存层（vnpy/trader/cached_datafeed.py）
- **用途**：实时交易和数据获取时的临时缓存
- **存储**：SQLite 数据库 + 可选 Parquet
- **特点**：支持多种数据源、自动过期清理、异步写入

### 2. AlphaLab 缓存层（vnpy/alpha/lab.py）
- **用途**：量化投研和回测的核心数据仓库
- **存储**：Parquet 文件（Polars 格式）
- **特点**：
  - **高性能**：列式存储，支持谓词下推和向量读取
  - **大容量**：适合存储多年历史数据
  - **标准化**：统一数据格式和类型
  - **可追溯**：支持版本管理和增量更新

### 3. 元信息管理层（vnpy/trader/stock_metadata.py）
- **用途**：统一管理所有股票的元信息和缓存状态
- **存储**：SQLite 数据库
- **核心功能**：
  - 记录上市/退市时间
  - 追踪缓存数据范围
  - 标记数据获取状态
  - 验证缓存一致性

### 缓存使用建议
| 场景 | 推荐缓存层 | 说明 |
|------|-----------|------|
| 实时行情订阅 | DataFeed 缓存 | 低延迟、高时效性 |
| 历史数据回测 | AlphaLab 缓存 | 高性能、大容量 |
| 因子计算研究 | AlphaLab 缓存 | 支持 DataFrame 批量操作 |
| 多数据源聚合 | 增强缓存层 | 自动处理数据一致性 |

## 测试方法

### 测试目录结构

```
tests/                              # 测试代码目录
├── alpha/                          # AI量化模块测试
│   ├── __init__.py
│   └── test_strategy.py            # 策略回测测试
├── chart/                          # 图表模块测试
│   └── __init__.py
├── datafeeds/                      # 数据服务测试
│   ├── __init__.py
│   └── test_tx_cache.py            # 腾讯缓存测试
├── event/                          # 事件引擎测试
│   └── __init__.py
├── rpc/                            # RPC模块测试
│   └── __init__.py
├── strategies/                     # 策略测试
│   └── __init__.py
├── trader/                         # 交易核心测试
│   └── __init__.py
├── README.md                       # 测试说明
├── test_akshare_a_stock.py         # AKShare股票数据测试
├── test_akshare_a_stock_simple.py  # AKShare简单测试
├── test_akshare_minimal.py         # AKShare最小化测试
├── test_alpha101.py                # Alpha101因子测试
├── test_async_fixes.py             # 异步修复测试
├── test_bar_chart.py               # K线图表测试
├── test_datafeed_integration.py    # 数据服务集成测试
├── test_default_cache_backend.py   # 默认缓存后端测试
├── test_sina_a_stock.py            # 新浪股票数据测试
├── test_strategy_backtest.py       # 策略回测测试
├── test_tqsdk_a_stock.py           # TQSDK股票数据测试
├── test_tqsdk_minimal.py           # TQSDK最小化测试
├── test_tx_cache_backtest.py       # 腾讯缓存回测测试
└── test_tx_datafeed.py             # 腾讯数据服务测试
```

### 测试工具和框架

| 工具 | 用途 | 版本要求 |
|------|------|----------|
| pytest | 测试框架 | >=7.0 |
| pytest-asyncio | 异步测试支持 | >=0.21 |
| pytest-cov | 覆盖率报告 | >=4.0 |

#### 回测策略测试
pyenv exec python3 strategies/lance_breitstein/backtest_lance_strategy.py

### 参考链接

- 项目根目录: `/Users/bytedance/src/vnpy/`
- 设计文档目录: `/Users/bytedance/src/vnpy/docs/design/`
- 核心代码目录: `/Users/bytedance/src/vnpy/vnpy/`
- 测试代码目录: `/Users/bytedance/src/vnpy/tests/`
