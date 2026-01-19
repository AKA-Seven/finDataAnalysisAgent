# utils/db_utils.py
"""
数据库工具模块
每次操作独立创建连接（简单、安全，避免连接池复杂性）
封装常用操作：
- 获取表格列表
- 获取表结构
- 执行查询（返回 list[dict]）
- 执行非查询语句（INSERT/UPDATE/DELETE）
后续扩展：支持事务、分页查询等
"""

import pymysql
from typing import List, Dict, Optional, Any, Tuple
from config import config

def get_connection(cursorclass=pymysql.cursors.DictCursor):
    """创建并返回一个新数据库连接（推荐在上下文管理器中使用）"""
    return pymysql.connect(
        host=config.DATABASE.host,
        port=config.DATABASE.port,
        user=config.DATABASE.user,
        password=config.DATABASE.password,
        database=config.DATABASE.db_name,
        charset=config.DATABASE.charset,
        connect_timeout=config.DATABASE.timeout,
        cursorclass=cursorclass,  # 默认 DictCursor，便于返回 dict
        autocommit=False,         # 非查询操作需手动 commit
    )

def get_tables() -> List[str]:
    """获取数据库所有表格名"""
    with get_connection(cursorclass=pymysql.cursors.Cursor) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            return [row[0] for row in cursor.fetchall()]

def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
    """获取指定表的字段结构（DESCRIBE）"""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"DESCRIBE `{table_name}`")
            return cursor.fetchall()

def execute_query(sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """执行SELECT查询，返回 list[dict]"""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()

def execute_non_query(sql: str, params: Optional[Tuple] = None) -> int:
    """执行INSERT/UPDATE/DELETE，返回受影响行数"""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor.rowcount

# 后续可扩展：事务上下文管理器、分页查询等