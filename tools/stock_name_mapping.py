#!/usr/bin/env python3
"""
股票代码到股票名称的映射工具
"""
import json
import os

# 预定义的股票代码到名称的映射（主要成分股）
STOCK_NAME_MAP = {
    # 沪市股票
    "600000.SSE": "浦发银行",
    "600004.SSE": "白云机场",
    "600006.SSE": "东风汽车",
    "600007.SSE": "中国国贸",
    "600008.SSE": "首创环保",
    "600009.SSE": "上海机场",
    "600010.SSE": "包钢股份",
    "600011.SSE": "华能国际",
    "600012.SSE": "皖通高速",
    "600015.SSE": "华夏银行",
    "600023.SSE": "浙能电力",
    "600025.SSE": "华能水电",
    "600027.SSE": "华电国际",
    "600036.SSE": "招商银行",
    "600089.SSE": "特变电工",
    "600115.SSE": "中国东航",
    "600161.SSE": "天坛生物",
    "600176.SSE": "中国巨石",
    "600233.SSE": "圆通速递",
    "600276.SSE": "恒瑞医药",
    "600346.SSE": "恒力石化",
    "600372.SSE": "中航电子",
    "600377.SSE": "宁沪高速",
    "600438.SSE": "通威股份",
    "600660.SSE": "福耀玻璃",
    "600690.SSE": "海尔智家",
    "600760.SSE": "中航沈飞",
    "600845.SSE": "宝信软件",
    "600926.SSE": "杭州银行",
    "601009.SSE": "南京银行",
    "601088.SSE": "中国神华",
    "601298.SSE": "青岛港",
    "601390.SSE": "中国中铁",
    "601607.SSE": "上海医药",
    "601698.SSE": "中国卫通",
    "601728.SSE": "中国电建",
    "601788.SSE": "光大证券",
    "601818.SSE": "光大银行",
    "601857.SSE": "中国石油",
    "601872.SSE": "招商轮船",
    "601898.SSE": "中煤能源",
    "601939.SSE": "建设银行",
    "601985.SSE": "中国核电",
    "603195.SSE": "公牛集团",
    "603260.SSE": "合盛硅业",
    "603369.SSE": "今世缘",
    "603392.SSE": "万泰生物",
    "603501.SSE": "韦尔股份",
    "605499.SSE": "东鹏控股",
    "688012.SSE": "中微公司",
    "688111.SSE": "金山办公",
    "688169.SSE": "石头科技",
    "688187.SSE": "时代电气",
    "688256.SSE": "寒武纪",
    
    # 深市股票
    "000001.SZ": "平安银行",
    "000002.SZ": "万科A",
    "000063.SZ": "中兴通讯",
    "000063.SZSE": "中兴通讯",
    "000408.SZ": "藏格矿业",
    "000408.SZSE": "藏格矿业",
    "000425.SZ": "徐工机械",
    "000425.SZSE": "徐工机械",
    "000596.SZ": "古井贡酒",
    "000596.SZSE": "古井贡酒",
    "000661.SZ": "长春高新",
    "000661.SZSE": "长春高新",
    "000792.SZ": "盐湖股份",
    "000792.SZSE": "盐湖股份",
    "000895.SZ": "双汇发展",
    "000895.SZSE": "双汇发展",
    "000975.SZ": "银泰黄金",
    "000975.SZSE": "银泰黄金",
    "000977.SZ": "浪潮信息",
    "000977.SZSE": "浪潮信息",
    "001979.SZ": "招商蛇口",
    "001979.SZSE": "招商蛇口",
    "002179.SZ": "中航光电",
    "002179.SZSE": "中航光电",
    "002241.SZ": "歌尔股份",
    "002241.SZSE": "歌尔股份",
    "002352.SZ": "顺丰控股",
    "002352.SZSE": "顺丰控股",
    "002463.SZ": "沪电股份",
    "002463.SZSE": "沪电股份",
    "002601.SZ": "中国太保",
    "002601.SZSE": "中国太保",
    "300274.SZ": "阳光电源",
    "300274.SZSE": "阳光电源",
    "300394.SZ": "天孚通信",
    "300394.SZSE": "天孚通信",
    "300413.SZ": "芒果超媒",
    "300413.SZSE": "芒果超媒",
    "300498.SZ": "温氏股份",
    "300498.SZSE": "温氏股份",
    "300759.SZ": "宁德时代",
    "300759.SZSE": "宁德时代",
    "300803.SZ": "指南针",
    "300803.SZSE": "指南针",
    
    # 指数
    "000300.SSE": "沪深300指数"
}


def get_stock_name(vt_symbol: str) -> str:
    """
    根据股票代码获取股票名称
    
    Args:
        vt_symbol: 股票代码，格式如 "600000.SSE" 或 "000001.SZ"
    
    Returns:
        股票名称，如果未找到则返回原代码
    """
    # 尝试直接查找
    if vt_symbol in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[vt_symbol]
    
    # 尝试去掉后缀查找（如 .SZSE -> .SZ）
    if vt_symbol.endswith(".SZSE"):
        short_symbol = vt_symbol[:-4] + ".SZ"
        if short_symbol in STOCK_NAME_MAP:
            return STOCK_NAME_MAP[short_symbol]
    
    # 尝试不带后缀
    code = vt_symbol.split(".")[0]
    if code in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[code]
    
    # 尝试添加常见后缀
    if not "." in vt_symbol:
        if code.startswith("6") or code.startswith("9") or code.startswith("7"):
            if f"{code}.SSE" in STOCK_NAME_MAP:
                return STOCK_NAME_MAP[f"{code}.SSE"]
        else:
            if f"{code}.SZ" in STOCK_NAME_MAP:
                return STOCK_NAME_MAP[f"{code}.SZ"]
            if f"{code}.SZSE" in STOCK_NAME_MAP:
                return STOCK_NAME_MAP[f"{code}.SZSE"]
    
    # 未找到，返回原代码
    return vt_symbol


def get_stock_code_with_name(vt_symbol: str) -> str:
    """
    获取带股票名称的代码显示字符串
    
    Args:
        vt_symbol: 股票代码
    
    Returns:
        格式如 "600000.SSE (浦发银行)" 的字符串
    """
    name = get_stock_name(vt_symbol)
    if name == vt_symbol:
        return vt_symbol
    return f"{vt_symbol} ({name})"


def save_stock_names_to_json(file_path: str = "stock_names.json"):
    """
    将股票名称映射保存到JSON文件
    
    Args:
        file_path: 输出文件路径
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(STOCK_NAME_MAP, f, ensure_ascii=False, indent=2)
    print(f"股票名称映射已保存到 {file_path}")


def load_stock_names_from_json(file_path: str = "stock_names.json") -> dict:
    """
    从JSON文件加载股票名称映射
    
    Args:
        file_path: 输入文件路径
    
    Returns:
        股票名称映射字典
    """
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


if __name__ == "__main__":
    # 测试
    test_codes = [
        "600000.SSE",
        "000001.SZ", 
        "000063.SZSE",
        "601728.SSE",
        "300759.SZSE",
        "000001.SZSE",  # 不存在的映射
    ]
    
    print("股票代码名称映射测试：")
    for code in test_codes:
        name = get_stock_name(code)
        print(f"{code} -> {name} -> {get_stock_code_with_name(code)}")
