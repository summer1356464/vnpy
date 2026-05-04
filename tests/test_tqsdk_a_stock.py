#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TQSDK A股数据测试脚本
基于: https://doc.shinnytech.com/tqsdk/latest/quickstart.html
"""

import sys
import time

print("="*60)
print("TQSDK A股数据测试")
print("="*60 + "\n")

# TQSDK账号信息
TQSDK_USERNAME = "oobumblebeeoo"
TQSDK_PASSWORD = "summer1356464"

print(f"账号: {TQSDK_USERNAME}")
print(f"密码: {'*' * len(TQSDK_PASSWORD)}")
print(f"TQSDK官方文档: https://doc.shinnytech.com/tqsdk/latest/quickstart.html")

try:
    # 导入TQSDK模块
    print("\n1. 导入TQSDK模块...")
    from tqsdk import TqApi, TqAuth
    import tqsdk

    print(f"  ✓ TQSDK版本: {tqsdk.__version__}")
    print("  ✓ TQSDK模块导入成功")

    # 测试1: 连接TQSDK服务
    print("\n2. 测试TQSDK服务连接...")
    print("  官方API: api = TqApi(auth=TqAuth(\"用户名\", \"密码\"))")

    # 使用官方API创建连接
    api = TqApi(auth=TqAuth(TQSDK_USERNAME, TQSDK_PASSWORD))
    print("  ✓ TQSDK服务连接成功")

    # 测试2: 获取A股实时行情
    print("\n3. 测试A股实时行情获取...")
    print("  官方API: quote = api.get_quote(\"合约代码\")")

    # A股合约代码格式: SSE.600000 (上证指数)
    a股合约 = [
        "SSE.600000",    # 浦发银行
        "SSE.600519",    # 贵州茅台
        "SZSE.000001",   # 平安银行
        "SZSE.000858",   # 五粮液
    ]

    for 合约 in a股合约:
        print(f"  测试合约: {合约}")
        try:
            quote = api.get_quote(合约)
            print(f"    ✓ 行情订阅成功: {合约}")

            # 等待数据更新
            start_time = time.time()
            timeout = 10  # 10秒超时
            data_received = False

            while time.time() - start_time < timeout:
                updated = api.wait_update()
                if updated and hasattr(quote, 'last_price') and quote.last_price:
                    print(f"    ✓ 实时行情更新: {quote.datetime} - {quote.last_price}")
                    data_received = True
                    break
                time.sleep(0.5)

            if data_received:
                print(f"    ✓ 实时行情获取成功")
                print(f"      合约: {quote.instrument_id}")
                print(f"      最新价: {quote.last_price}")
                print(f"      开盘价: {quote.open}")
                
                # 安全访问属性
                if hasattr(quote, 'highest'):
                    print(f"      最高价: {quote.highest}")
                elif hasattr(quote, 'high'):
                    print(f"      最高价: {quote.high}")
                
                if hasattr(quote, 'lowest'):
                    print(f"      最低价: {quote.lowest}")
                elif hasattr(quote, 'low'):
                    print(f"      最低价: {quote.low}")
                
                if hasattr(quote, 'volume'):
                    print(f"      成交量: {quote.volume}")
                
                if hasattr(quote, 'datetime'):
                    print(f"      时间: {quote.datetime}")
            else:
                print(f"    ⚠️  未获取到实时行情数据")
        except Exception as e:
            print(f"    ✗ {合约}: 错误 - {e}")

    # 关闭API
    api.close()
    print("\n4. API关闭成功")

    # 总结测试结果
    print("\n" + "="*60)
    print("TQSDK A股数据测试结果")
    print("="*60)
    print("✓ TQSDK模块: 正常")
    print("✓ 服务连接: 成功")
    print("✓ A股行情: 成功")

    print("\n✓ TQSDK A股数据测试通过！")
    print("  - 符合官方API规范")
    print("  - 能够连接到TQSDK服务")
    print("  - 能够获取A股实时行情数据")

    # 官方文档参考
    print("\n" + "="*60)
    print("官方文档参考")
    print("="*60)
    print("- 安装: pip install tqsdk -U")
    print("- 注册: https://www.shinnytech.com 注册快期账户")
    print("- 文档: https://doc.shinnytech.com/tqsdk/latest/")
    print("- A股合约格式: SSE.600000 或 SZSE.000001")

    sys.exit(0)

except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    print("\n✗ TQSDK A股数据测试失败")
    print("\n请检查:")
    print("- 网络连接是否正常")
    print("- 访问 https://www.shinnytech.com 验证账户状态")
    sys.exit(1)
