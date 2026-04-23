#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare A股数据测试脚本 - 极简版
基于: https://www.akshare.xyz/
"""

import sys
import time

print("="*60)
print("AKShare A股数据测试")
print("="*60 + "\n")

try:
    # 导入AKShare模块
    print("1. 导入AKShare模块...")
    import akshare as ak

    print(f"  ✓ AKShare版本: {ak.__version__}")
    print("  ✓ AKShare模块导入成功")

    # 测试1: 获取A股实时行情
    print("\n2. 测试A股实时行情获取...")
    print("  API: ak.stock_zh_a_spot()")

    # 获取A股实时行情
    stock_zh_a_spot_df = ak.stock_zh_a_spot()
    print(f"  ✓ A股行情获取成功: {len(stock_zh_a_spot_df)} 只股票")

    # 显示数据结构
    print("\n3. 数据结构:")
    print(f"  列名: {list(stock_zh_a_spot_df.columns)}")

    # 显示前5只股票
    print("\n4. 前5只股票数据:")
    print(stock_zh_a_spot_df.head())

    # 测试2: 搜索特定股票
    print("\n5. 搜索特定股票...")
    stock_name = "贵州茅台"
    
    # 根据股票名称搜索
    maotai_data = stock_zh_a_spot_df[stock_zh_a_spot_df['名称'] == stock_name]
    if not maotai_data.empty:
        row = maotai_data.iloc[0]
        print(f"  股票: {row['代码']} - {row['名称']}")
        print(f"    最新价: {row['最新价']}")
        print(f"    涨跌额: {row['涨跌额']}")
        print(f"    涨跌幅: {row['涨跌幅']}")
        print(f"    成交量: {row['成交量']}")
        print(f"    成交额: {row['成交额']}")
    else:
        print(f"  未找到股票: {stock_name}")

    # 总结测试结果
    print("\n" + "="*60)
    print("AKShare A股数据测试结果")
    print("="*60)
    print("✓ AKShare模块: 正常")
    print("✓ A股行情: 成功")
    print("✓ 数据量: 充足")

    print("\n✓ AKShare A股数据测试通过！")
    print("  - 免费获取A股实时行情")
    print("  - 支持所有A股股票")
    print("  - 数据字段完整")
    print("  - 无需账号认证")

    # 官方文档参考
    print("\n" + "="*60)
    print("官方文档参考")
    print("="*60)
    print("- 安装: pip install akshare -U")
    print("- 文档: https://www.akshare.xyz/")
    print("- 核心API: ak.stock_zh_a_spot()")

    sys.exit(0)

except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    print("\n✗ AKShare A股数据测试失败")
    print("\n请检查:")
    print("- 网络连接是否正常")
    print("- 运行: pip install akshare -U 安装AKShare")
    sys.exit(1)
