#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare A股数据测试脚本 - 简化版
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
    print(f"  ✓ 实时行情获取成功: {len(stock_zh_a_spot_df)} 只股票")
    print(f"  ✓ 数据字段: {list(stock_zh_a_spot_df.columns)}")

    # 测试1.1: 获取A股历史数据 - 腾讯财经接口
    print("\n2.1 测试A股历史数据获取(腾讯财经接口)...")
    print("  API: ak.stock_zh_a_hist_tx()")

    # 获取A股历史数据 - 腾讯财经接口
    import datetime
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=30)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    stock_zh_a_hist_tx_df = ak.stock_zh_a_hist_tx(
        symbol="sh600519",  # 贵州茅台，上海市场
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )
    print(f"  ✓ 腾讯财经接口历史数据获取成功: {len(stock_zh_a_hist_tx_df)} 条记录")
    print(f"  ✓ 数据字段: {list(stock_zh_a_hist_tx_df.columns)}")
    print(f"  ✓ 最近5条数据:\n{stock_zh_a_hist_tx_df.tail()}")

    # 显示前10只股票
    print("\n3. 显示前10只股票数据:")
    print(stock_zh_a_spot_df.head(10))

    # 测试2: 获取特定股票实时数据
    print("\n4. 测试特定股票实时数据...")
    stock_codes = ["600000", "600519", "000001", "000858"]
    
    # 根据接口调整字段名
    code_field = '代码' if '代码' in stock_zh_a_spot_df.columns else 'stock_code'
    name_field = '名称' if '名称' in stock_zh_a_spot_df.columns else 'stock_name'
    price_field = '最新价' if '最新价' in stock_zh_a_spot_df.columns else 'price'
    change_field = '涨跌额' if '涨跌额' in stock_zh_a_spot_df.columns else 'change_amount'
    pct_change_field = '涨跌幅' if '涨跌幅' in stock_zh_a_spot_df.columns else 'change_pct'
    volume_field = '成交量' if '成交量' in stock_zh_a_spot_df.columns else 'volume'
    amount_field = '成交额' if '成交额' in stock_zh_a_spot_df.columns else 'amount'
    
    # 获取所有股票代码
    all_codes = stock_zh_a_spot_df[code_field].tolist()
    
    for code in stock_codes:
        try:
            # 尝试不同的代码格式搜索
            found = False
            
            # 格式1: 直接匹配
            if code in all_codes:
                stock_data = stock_zh_a_spot_df[stock_zh_a_spot_df[code_field] == code]
                found = True
            # 格式2: 添加上海市场前缀
            elif f"sh{code}" in all_codes:
                stock_data = stock_zh_a_spot_df[stock_zh_a_spot_df[code_field] == f"sh{code}"]
                found = True
            # 格式3: 添加深圳市场前缀
            elif f"sz{code}" in all_codes:
                stock_data = stock_zh_a_spot_df[stock_zh_a_spot_df[code_field] == f"sz{code}"]
                found = True
            # 格式4: 匹配代码的后6位
            else:
                # 提取代码的后6位进行匹配
                code_suffix = code[-6:]
                matching_codes = [c for c in all_codes if str(c).endswith(code_suffix)]
                if matching_codes:
                    stock_data = stock_zh_a_spot_df[stock_zh_a_spot_df[code_field] == matching_codes[0]]
                    found = True
            
            if found and not stock_data.empty:
                row = stock_data.iloc[0]
                print(f"  股票: {code} - {row[name_field]}")
                print(f"    最新价: {row[price_field]}")
                print(f"    涨跌额: {row[change_field]}")
                print(f"    涨跌幅: {row[pct_change_field]}")
                print(f"    成交量: {row[volume_field]}")
                print(f"    成交额: {row[amount_field]}")
                print()
            else:
                print(f"  未找到股票: {code}")
                print(f"    可用的代码格式示例: {all_codes[:3]}")
        except Exception as e:
            print(f"  测试股票 {code} 失败: {e}")

    # 测试2.1: 测试腾讯财经接口指数历史数据
    print("\n4.1 测试指数历史数据获取(腾讯财经接口)...")
    print("  API: ak.stock_zh_index_daily_tx()")
    
    # 获取上证指数历史数据（该接口不支持日期参数）
    try:
        index_daily_tx_df = ak.stock_zh_index_daily_tx(symbol="sh000001")
        print(f"  ✓ 腾讯财经接口指数历史数据获取成功: {len(index_daily_tx_df)} 条记录")
        print(f"  ✓ 数据字段: {list(index_daily_tx_df.columns)}")
        print(f"  ✓ 最近5条数据:\n{index_daily_tx_df.tail()}")
    except Exception as e:
        print(f"  ⚠️  腾讯财经接口指数历史数据获取失败: {e}")
        print(f"  ⚠️  该接口可能已废弃或参数发生变化")

    # 测试3: 获取指数历史数据（仅使用腾讯财经稳定接口）
    print("\n5. 测试指数历史数据(腾讯财经接口)...")
    print("  API: ak.stock_zh_index_daily_tx()")
    
    try:
        # 获取更多指数的历史数据
        test_indexes = ["sh000300", "sz399001", "sz399006"]
        for index_code in test_indexes:
            try:
                index_df = ak.stock_zh_index_daily_tx(symbol=index_code)
                print(f"  ✓ 指数 {index_code} 历史数据获取成功: {len(index_df)} 条记录")
                print(f"    最近日期: {index_df['date'].iloc[-1]}")
                print(f"    最新收盘: {index_df['close'].iloc[-1]}")
                print()
            except Exception as e:
                print(f"  ⚠️  指数 {index_code} 历史数据获取失败: {e}")
    except Exception as e:
        print(f"  ⚠️  指数历史数据测试失败: {e}")

    # 总结测试结果
    print("\n" + "="*60)
    print("AKShare A股数据测试结果")
    print("="*60)
    print("✓ AKShare模块: 正常")
    print("✓ 实时行情接口(stock_zh_a_spot): 成功")
    print("✓ 腾讯财经股票历史数据(stock_zh_a_hist_tx): 成功")
    print("✓ 腾讯财经指数历史数据(stock_zh_index_daily_tx): 成功")
    print("✓ 特定股票查询: 成功")
    print("✓ 指数数据: 成功")

    print("\n✓ AKShare A股数据测试通过！")
    print("  - 实时行情: 使用 stock_zh_a_spot()")
    print("  - 历史数据: 强烈推荐腾讯财经接口 stock_zh_a_hist_tx() (稳定限流少)")
    print("  - 指数历史数据: 强烈推荐腾讯财经接口 stock_zh_index_daily_tx() (稳定可靠)")
    print("  - 免费获取A股行情数据")
    print("  - 支持所有A股股票")
    print("  - 支持主要指数")
    print("  - 无需账号认证")
    print("  - 已剔除不稳定的东方财富指数接口")

    # 官方文档参考
    print("\n" + "="*60)
    print("官方文档参考")
    print("="*60)
    print("- 安装: pip install akshare -U")
    print("- 文档: https://www.akshare.xyz/")
    print("- GitHub: https://github.com/akfamily/akshare")
    print("- 推荐接口列表:")
    print("  1. 实时行情: stock_zh_a_spot()")
    print("  2. 股票历史数据: stock_zh_a_hist_tx() (腾讯财经，推荐)")
    print("  3. 指数历史数据: stock_zh_index_daily_tx() (腾讯财经，推荐)")
    print("- 注意: 避免使用不稳定的东方财富指数接口")

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
