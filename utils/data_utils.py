"""
数据工具：提供数据格式标准化、类型转换、序列化等通用能力
"""
import pandas as pd
from typing import Dict, List, Any, Optional

def standardize_data_format(data: Any) -> Any:
    """
    数据格式标准化（统一处理空值、特殊字符）
    :param data: 原始数据（支持字典、列表、DataFrame）
    :return: 标准化后的数据
    """
    if data is None:
        return {}

    if isinstance(data, pd.DataFrame):
        return df_to_dict_list(data)

    if isinstance(data, list):
        return [_standardize_dict_item(item) for item in data]

    if isinstance(data, dict):
        return _standardize_dict_item(data)

    return data

def _standardize_dict_item(data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """标准化字典项（内部辅助方法）"""
    standardized = {}
    for key, value in data_dict.items():
        # 处理空值
        if pd.isna(value) or value == "":
            standardized[key] = None
        # 处理数字格式
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            standardized[key] = round(value, 2) if isinstance(value, float) else value
        # 处理日期格式（简单适配）
        elif isinstance(value, str) and "-" in value and len(value) == 10:
            standardized[key] = value
        else:
            standardized[key] = value
    return standardized

def convert_data_type(data: Any, target_type: type) -> Any:
    """
    数据类型转换（兼容常见类型）
    :param data: 原始数据
    :param target_type: 目标类型（int/float/str/bool）
    :return: 转换后数据
    """
    if data is None:
        return None

    try:
        if target_type == int:
            return int(float(data))
        elif target_type == float:
            return float(data)
        elif target_type == str:
            return str(data)
        elif target_type == bool:
            return bool(data)
        else:
            return data
    except (ValueError, TypeError):
        return None

def df_to_dict_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Pandas DataFrame 转 列表字典格式（便于序列化/传输）
    :param df: 原始DataFrame
    :return: 列表字典
    """
    return df.to_dict("records")

def dict_list_to_df(dict_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    列表字典 转 Pandas DataFrame
    :param dict_list: 列表字典
    :return: DataFrame
    """
    return pd.DataFrame(dict_list)

def fill_missing_value(data: List[Dict[str, Any]], fill_value: Any = None) -> List[Dict[str, Any]]:
    """
    填充缺失值
    :param data: 列表字典数据
    :param fill_value: 填充值
    :return: 填充后数据
    """
    if not data:
        return []

    # 获取所有字段名
    all_fields = set()
    for item in data:
        all_fields.update(item.keys())

    # 填充缺失字段
    filled_data = []
    for item in data:
        filled_item = item.copy()
        for field in all_fields:
            if field not in filled_item:
                filled_item[field] = fill_value
        filled_data.append(filled_item)

    return filled_data