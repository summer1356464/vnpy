# 测试框架设计

## 概述

本项目采用基于pytest的测试框架，遵循最佳实践组织测试代码，确保代码质量和可维护性。

## 测试目录结构

```
tests/
├── alpha/              # Alpha策略模块测试
├── chart/              # 图表模块测试
├── datafeeds/          # 数据源模块测试
├── event/              # 事件模块测试
├── rpc/                # RPC模块测试
├── strategies/         # 策略实现测试
├── trader/             # 交易核心模块测试
├── __init__.py
└── README.md
```

## 测试类型分类

### 1. 单元测试 (Unit Tests)

- 测试单个函数或类的功能
- 运行速度快
- 隔离性强，依赖少
- 标记：`@pytest.mark.unit`

### 2. 集成测试 (Integration Tests)

- 测试多个模块之间的交互
- 验证系统各部分协同工作
- 标记：`@pytest.mark.integration`

### 3. 功能测试 (Functional Tests)

- 测试完整的功能流程
- 验证业务逻辑正确性
- 标记：`@pytest.mark.functional`

### 4. 性能测试 (Performance Tests)

- 测试系统性能和响应时间
- 标记：`@pytest.mark.performance`

### 5. 慢测试 (Slow Tests)

- 运行时间较长的测试
- 可以选择性跳过
- 标记：`@pytest.mark.slow`

## 模块特定标记

- `@pytest.mark.alpha`: Alpha策略相关测试
- `@pytest.mark.chart`: 图表相关测试
- `@pytest.mark.datafeed`: 数据源相关测试
- `@pytest.mark.event`: 事件系统相关测试
- `@pytest.mark.rpc`: RPC通信相关测试
- `@pytest.mark.strategy`: 策略相关测试
- `@pytest.mark.trader`: 交易核心相关测试
- `@pytest.mark.tx`: 腾讯数据源相关测试
- `@pytest.mark.cache`: 缓存系统相关测试

## 测试文件命名规范

```
test_<module_name>_<feature_name>.py
```

**示例：**
- `test_tx_cache.py`: 测试TX数据源的缓存功能
- `test_strategy_backtesting.py`: 测试策略回测功能
- `test_data_query.py`: 测试数据查询功能

## 测试类和函数命名规范

### 测试类
```python
class Test<ClassName>:
    pass
```

### 测试函数
```python
def test_<function_name>_<scenario>:
    pass
```

**示例：**
```python
def test_data_query_success():
    pass

def test_data_query_failure():
    pass
```

## pytest配置

测试框架使用pytest.ini进行配置，主要配置项包括：

- 测试文件和目录模式
- 测试报告格式
- 忽略的目录
- 环境变量
- 测试标记

## 测试运行方式

### 运行所有测试

```bash
pytest
```

### 运行特定目录的测试

```bash
pytest tests/alpha/
```

### 运行特定文件的测试

```bash
pytest tests/datafeeds/test_tx_cache.py
```

### 运行特定测试函数

```bash
pytest tests/datafeeds/test_tx_cache.py::test_tx_data_query
```

### 运行特定标记的测试

```bash
# 运行所有单元测试
pytest -m unit

# 运行所有TX数据源相关测试
pytest -m tx

# 运行单元测试和TX数据源测试
pytest -m "unit and tx"

# 运行除了慢测试之外的所有测试
pytest -m "not slow"
```

### 生成测试覆盖率报告

```bash
# 安装pytest-cov
pip install pytest-cov

# 生成覆盖率报告
pytest --cov=vnpy --cov-report=html:coverage_report
```

## 测试最佳实践

### 1. 使用Fixture管理测试资源

```python
@pytest.fixture
def setup_test_env():
    # 准备测试环境
    env = TestEnvironment()
    env.setup()
    
    yield env
    
    # 清理测试环境
    env.teardown()
```

### 2. 参数化测试

```python
@pytest.mark.parametrize("param1,param2,expected", [
    (1, 2, 3),
    (4, 5, 9),
    (10, 20, 30)
])
def test_addition(param1, param2, expected):
    assert param1 + param2 == expected
```

### 3. 断言清晰

```python
# 不好的断言
assert result

# 好的断言
assert result is not None
assert len(result) > 0
assert result["key"] == expected_value
```

### 4. 测试隔离

- 每个测试应该独立运行
- 测试之间不应该共享状态
- 使用fixture确保测试环境的干净

### 5. 测试文档

- 为测试函数添加清晰的文档字符串
- 说明测试的目的和预期结果
- 记录测试的前置条件

## 迁移现有测试

### 步骤1: 分析现有测试

- 了解测试的功能和范围
- 确定测试所属的模块
- 识别测试类型

### 步骤2: 创建新的测试文件

- 按照命名规范创建新的测试文件
- 放置在对应的模块目录下

### 步骤3: 重构测试代码

- 使用pytest的语法和特性
- 添加适当的标记
- 使用fixture管理测试资源
- 编写清晰的断言

### 步骤4: 运行和验证

- 运行新的测试文件
- 确保测试通过
- 验证测试覆盖率

## 示例测试文件

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试示例
"""

import pytest
from vnpy.module import MyClass


@pytest.fixture
def my_instance():
    """创建测试实例"""
    return MyClass()


@pytest.mark.unit
def test_my_method(my_instance):
    """测试MyClass的my_method方法"""
    result = my_instance.my_method(1, 2)
    assert result == 3
    assert isinstance(result, int)


@pytest.mark.parametrize("a,b,expected", [(1, 2, 3), (4, 5, 9)])
def test_my_method_params(my_instance, a, b, expected):
    """测试my_method方法的不同参数组合"""
    result = my_instance.my_method(a, b)
    assert result == expected
```

## 常见问题

### 1. 测试失败怎么办？

- 检查测试代码和被测试代码
- 使用`pytest -v`查看详细输出
- 使用`pytest --tb=long`查看完整的堆栈跟踪

### 2. 如何调试测试？

- 在测试代码中添加断点
- 使用`pytest --pdb`进入调试模式

### 3. 如何处理测试依赖？

- 使用fixture管理依赖
- 使用mock模拟外部依赖
- 考虑使用测试容器

## 总结

通过采用规范的测试框架和最佳实践，可以提高测试的质量和可维护性，确保项目的稳定性和可靠性。

建议团队成员：
1. 遵循测试命名和结构规范
2. 编写清晰、独立的测试
3. 定期运行测试
4. 维护测试覆盖率
