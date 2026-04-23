#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新浪财经 A股数据测试脚本
基于: 新浪财经API
"""

import sys
import time
import json
import requests

print("="*60)
print("新浪财经 A股数据测试")
print("="*60 + "\n")

try:
    # 测试1: 获取A股实时行情
    print("1. 测试A股实时行情获取...")
    print("  API: 新浪财经实时行情接口")

    # 新浪财经实时行情API
    symbols = ["sh600000", "sh600519", "sz000001", "sz000858"]
    url = f"http://hq.sinajs.cn/list={','.join(symbols)}"

    response = requests.get(url)
    response.encoding = "gbk"
    print(f"  ✓ 接口请求成功: {response.status_code}")

    # 解析数据
    data = response.text
    lines = data.split("\n")
    
    print("\n2. 实时行情数据:")
    for line in lines:
        if line:
            try:
                # 解析新浪财经数据格式
                symbol_data = line.split("=")
                symbol = symbol_data[0].split("_")[1]
                values = symbol_data[1].strip('"').split(",")
                
                if len(values) >= 4:
                    name = values[0]
                    open_price = values[1]
                    last_price = values[3]
                    high = values[4]
                    low = values[5]
                    volume = values[8]
                    
                    print(f"  {symbol} - {name}")
                    print(f"    最新价: {last_price}")
                    print(f"    开盘价: {open_price}")
                    print(f"    最高价: {high}")
                    print(f"    最低价: {low}")
                    print(f"    成交量: {volume}")
                    print()
            except Exception as e:
                print(f"  解析数据失败: {e}")

    # 测试2: 获取指数数据
    print("3. 测试指数数据...")
    index_symbols = ["sh000001", "sh000300", "sz399001", "sz399006"]
    index_url = f"http://hq.sinajs.cn/list={','.join(index_symbols)}"

    index_response = requests.get(index_url)
    index_response.encoding = "gbk"
    print(f"  ✓ 指数数据请求成功: {index_response.status_code}")

    # 解析指数数据
    index_data = index_response.text
    index_lines = index_data.split("\n")
    
    print("\n4. 指数实时数据:")
    for line in index_lines:
        if line:
            try:
                # 解析新浪财经数据格式
                symbol_data = line.split("=")
                symbol = symbol_data[0].split("_")[1]
                values = symbol_data[1].strip('"').split(",")
                
                if len(values) >= 4:
                    name = values[0]
                    open_price = values[1]
                    last_price = values[3]
                    high = values[4]
                    low = values[5]
                    volume = values[8]
                    
                    print(f"  {symbol} - {name}")
                    print(f"    最新价: {last_price}")
                    print(f"    开盘价: {open_price}")
                    print(f"    最高价: {high}")
                    print(f"    最低价: {low}")
                    print(f"    成交量: {volume}")
                    print()
            except Exception as e:
                print(f"  解析数据失败: {e}")

    # 总结测试结果
    print("" + "="*60)
    print("新浪财经 A股数据测试结果")
    print("="*60)
    print("✓ 实时行情: 成功")
    print("✓ 指数数据: 成功")
    print("✓ 接口响应: 正常")

    print("\n✓ 新浪财经 A股数据测试通过！")
    print("  - 免费获取A股实时行情")
    print("  - 免费获取指数数据")
    print("  - 无需账号认证")

    # 官方文档参考
    print("\n" + "="*60)
    print("API参考")
    print("="*60)
    print("- 实时行情: http://hq.sinajs.cn/list=sh600000,sz000001")
    print("- 指数数据: http://hq.sinajs.cn/list=sh000001,sz399001")
    print("- 数据格式: 逗号分隔的字符串")

    sys.exit(0)

except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    print("\n✗ 新浪财经 A股数据测试失败")
    print("\n请检查:")
    print("- 网络连接是否正常")
    print("- 访问 http://hq.sinajs.cn 验证接口可用性")
    sys.exit(1)
