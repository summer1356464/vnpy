#!/usr/bin/env python3
"""
获取沪深300成分股列表
"""
import akshare as ak
import pandas as pd


def get_hs300_constituents() -> list:
    """
    获取沪深300成分股列表
    
    Returns:
        list: 沪深300成分股代码列表，格式为["600000.SSE", "000001.SZ"]
    """
    try:
        # 使用akshare获取沪深300成分股
        df = ak.index_stock_cons(symbol="000300")
        
        # 添加交易所后缀
        stocks = []
        for code in df["品种代码"]:
            if code.startswith("6"):
                # 沪市股票
                stocks.append(f"{code}.SSE")
            else:
                # 深市股票 - 使用SZSE作为交易所代码
                stocks.append(f"{code}.SZSE")
        
        print(f"成功获取沪深300成分股 {len(stocks)} 只")
        return stocks
    except Exception as e:
        print(f"获取沪深300成分股失败: {e}")
        # 返回备用列表
        return [
            "000001.SZ", "000002.SZ", "000008.SZ", "000009.SZ", "000012.SZ",
            "000021.SZ", "000024.SZ", "000027.SZ", "000039.SZ", "000046.SZ",
            "600000.SSE", "600004.SSE", "600006.SSE", "600007.SSE", "600008.SSE",
            "600009.SSE", "600010.SSE", "600011.SSE", "600012.SSE", "600015.SSE"
        ]


if __name__ == "__main__":
    stocks = get_hs300_constituents()
    print(f"前10只成分股: {stocks[:10]}")
    print(f"成分股总数: {len(stocks)}")
