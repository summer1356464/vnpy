#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare A股数据测试脚本
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

    # 显示前10只股票
    print("\n3. 显示前10只股票数据:")
    print(stock_zh_a_spot_df.head(10))

    # 测试2: 获取特定股票详情
    print("\n4. 测试特定股票详情...")
    stock_code = "600000"
    print(f"  测试股票: {stock_code} (浦发银行)")

    # 获取股票历史数据
    stock_zh_a_daily_df = ak.stock_zh_a_daily(symbol=stock_code)
    print(f"  ✓ 历史数据获取成功: {len(stock_zh_a_daily_df)} 条记录")

    # 显示最近10条历史数据
    print("\n5. 显示最近10条历史数据:")
    print(stock_zh_a_daily_df.tail(10))

    # 测试3: 获取指数数据
    print("\n6. 测试指数数据...")
    index_code = "sh000001"
    print(f"  测试指数: {index_code} (上证指数)")

    # 获取指数历史数据
    index_df = ak.stock_zh_index_daily(symbol=index_code)
    print(f"  ✓ 指数数据获取成功: {len(index_df)} 条记录")

    # 显示最近10条指数数据
    print("\n7. 显示最近10条指数数据:")
    print(index_df.tail(10))

    # 测试4: 获取行业数据
    print("\n8. 测试行业数据...")
    print("  API: ak.stock_board_industry_name_ths()")

    # 获取行业列表
    industry_df = ak.stock_board_industry_name_ths()
    print(f"  ✓ 行业数据获取成功: {len(industry_df)} 个行业")

    # 显示前10个行业
    print("\n9. 显示前10个行业:")
    print(industry_df.head(10))

    # 总结测试结果
    print("\n" + "="*60)
    print("AKShare A股数据测试结果")
    print("="*60)
    print("✓ AKShare模块: 正常")
    print("✓ A股行情: 成功")
    print("✓ 股票历史数据: 成功")
    print("✓ 指数数据: 成功")
    print("✓ 行业数据: 成功")

    print("\n✓ AKShare A股数据测试通过！")
    print("  - 免费获取A股实时行情")
    print("  - 免费获取历史数据")
    print("  - 支持指数和行业数据")

    # 官方文档参考
    print("\n" + "="*60)
    print("官方文档参考")
    print("="*60)
    print("- 安装: pip install akshare -U")
    print("- 文档: https://www.akshare.xyz/")
    print("- GitHub: https://github.com/akfamily/akshare")

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
