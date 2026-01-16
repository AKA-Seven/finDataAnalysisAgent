# -*- coding: utf-8 -*-
"""
NL2SQL模块（nl2sql）
核心功能：自然语言查询 → 数据库Schema提取 → 生成返回Pandas DataFrame的Python查询代码
适配场景：学生管理系统数据库查询，生成的代码可直接对接Python沙箱安全执行
核心特性：仅生成代码不执行、参数化配置、支持DeepSeek大模型、返回标准化DataFrame
"""

# 导入模块内核心类（与模块内的核心文件名称对应，确保类名一致）
from .sql_generator import (
    SQLGenerator
)

# 定义公共API（外部导入时，仅暴露以下核心对象，隐藏内部辅助逻辑）
__all__ = [
    "SQLGenerator"           # 核心入口类（整合Schema提取+代码生成，一键调用）
]

# 模块版本信息（便于后续迭代管理、问题排查）
__version__ = "1.0.0"

# 模块默认配置（可选，提供全局默认值，可被外部配置覆盖）
from typing import Dict

# 默认DeepSeek配置（贴合用户提供的配置格式，仅作兜底）
DEFAULT_DEEPSEEK_CONFIG: Dict = {
    "API_KEY": "",
    "BASE_URL": "https://api.deepseek.com",
    "MODEL": "deepseek-chat",
    "ENDPOINT": "/v1/chat/completions"
}

# 默认MySQL配置（贴合学生管理系统，仅作兜底）
DEFAULT_MYSQL_CONFIG: Dict = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "db": "school_student_management_system",
    "charset": "utf8mb4",
    "db_type": "mysql"
}