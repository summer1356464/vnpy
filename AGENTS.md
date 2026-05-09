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
│   └── strategy/                  # 策略投研开发
├── chart/                         # K线图表模块
├── event/                         # 事件驱动引擎
├── rpc/                           # 跨进程通信模块
└── trader/                        # 交易核心模块
    └── ui/                        # 用户界面组件

docs/                              # 文档目录
├── community/                     # 社区文档
├── elite/                         # 精英版文档
└── design/                        # 设计文档（本目录）

examples/                          # 示例代码
tests/                             # 测试代码
strategies/                        # 策略实现
tools/                             # 工具脚本
```

## 核心模块入口

| 模块 | 核心文件 | 主要职责 |
|------|----------|----------|
| 交易核心 | vnpy/trader/engine.py | 订单管理、账户管理、事件处理 |
| AI量化 | vnpy/alpha/lab.py | 投研流程管理 |
| 回测引擎 | vnpy/alpha/strategy/backtesting.py | 策略回测 |
| 事件引擎 | vnpy/event/engine.py | 事件分发和处理 |
| 数据缓存 | vnpy/trader/cached_datafeed.py | 本地数据缓存 |

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
