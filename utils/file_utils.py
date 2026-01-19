# utils/file_utils.py
"""
文件工具模块（路径、输出管理、表格数据辅助）
主要功能：
- 统一输出路径管理（自动创建outputs目录）
- DataFrame 或 list[list] 转表格数据格式（供Word/Excel工具使用）
  - pandas DataFrame：自动添加表头，None/NaN 转为 ""
  - list[list]：直接转换，None 转为 ""（保持与pandas一致）
- 简单文件读写辅助
后续扩展：日志统一管理、模板路径管理、图片插入辅助等
"""

from pathlib import Path
from typing import Union, List, Any
import pandas as pd
from config import config

def get_output_path(filename: str) -> Path:
    """
    获取标准化输出路径（在 outputs/ 目录下）
    自动创建必要的子目录
    """
    path = config.OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.resolve()

def df_to_table_data(df: Union[pd.DataFrame, List[List[Any]]]) -> List[List[str]]:
    """
    将 pandas DataFrame 或 list[list] 转换为通用表格数据
    - pandas：自动添加表头，缺失值（None/NaN）转为 ""
    - list[list]：直接字符串化，None 转为 ""（与pandas行为一致）
    - 返回 list[list[str]]，每行是一个list
    供 Word/Excel 工具直接插入表格使用
    """
    if isinstance(df, pd.DataFrame):
        # 表头 + 数据
        headers = [str(col) for col in df.columns]
        rows = df.fillna("").astype(str).values.tolist()
        return [headers] + rows
    else:
        # list[list]：处理 None 为 ""，其他 str()
        return [[str(cell) if cell is not None else "" for cell in row] for row in df]

def save_text_to_file(content: str, filename: str) -> Path:
    """简单文本保存辅助（调试用）"""
    path = get_output_path(filename)
    path.write_text(content, encoding="utf-8")
    return path

# 后续可扩展：
# - 统一的logging setup（logging.basicConfig + get_logger）
# - 模板文件路径管理（e.g., get_template_path("report_template.docx")）
# - 图片/附件处理辅助