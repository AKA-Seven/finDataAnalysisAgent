"""
Office解析模块
支持Excel/Word的读取、写入、模板解析、数据提取与填充
"""

from .excel_parser import ExcelOperator
from .word_parser import WordOperator

__all__ = ["ExcelOperator", "WordOperator"]