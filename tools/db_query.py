# tools/db_query.py
"""
数据库查询工具（优化大数据：默认limit + 摘要）
支持三种操作：list_tables, get_schema, query_data
query_data：返回样本 + pandas摘要（避免全数据浪费token）
"""

import json
import pandas as pd
from utils.db_utils import get_tables, get_table_schema, execute_query
from utils.file_utils import df_to_table_data
from tools.base_tool import BaseTool

class DBQueryTool(BaseTool):
    name = "db_query"
    description = """查询数据库（安全、非任意SQL）。
输入JSON: 
- {"action": "list_tables"}
- {"action": "get_schema", "table_name": "xxx"}
- {"action": "query_data", "sql": "SELECT ...", "limit": 100 (可选，默认100)}"""

    def run(self, input_str: str) -> str:
        try:
            data = json.loads(input_str)
            action = data["action"]
        except (json.JSONDecodeError, KeyError):
            return "错误：输入必须为JSON，且包含'action'字段"

        if action == "list_tables":
            tables = get_tables()
            return f"数据库表格列表（共{len(tables)}个）：\n" + ", ".join(tables)

        elif action == "get_schema":
            table_name = data.get("table_name")
            if not table_name:
                return "错误：get_schema需要table_name"
            schema = get_table_schema(table_name)
            lines = [f"- {col['Field']}: {col['Type']} ({'NULL' if col['Null']=='YES' else 'NOT NULL'})" for col in schema]
            return f"表 `{table_name}` 结构：\n" + "\n".join(lines)

        elif action == "query_data":
            sql = data.get("sql", "").strip()
            limit = int(data.get("limit", 100))
            if not sql.upper().startswith("SELECT"):
                return "错误：仅支持SELECT查询"
            sql = sql if sql.upper().endswith("LIMIT") else f"{sql} LIMIT {limit}"

            try:
                raw_data = execute_query(sql)
                if not raw_data:
                    return "查询无结果"
                df = pd.DataFrame(raw_data)

                # 样本 + 摘要（大数据优化）
                head = df.head(10)
                tail = df.tail(10) if len(df) > 20 else pd.DataFrame()
                summary = df.describe(include='all').fillna("").astype(str)

                result = f"查询结果（总行数：{len(df)}，显示样本）:\n\n前10行：\n"
                result += "\n".join([" | ".join(map(str, row)) for row in df_to_table_data(head)])
                if not tail.empty:
                    result += "\n\n后10行：\n" + "\n".join([" | ".join(map(str, row)) for row in df_to_table_data(tail)])
                result += "\n\n统计摘要：\n" + "\n".join([" | ".join(map(str, row)) for row in df_to_table_data(summary)])
                return result
            except Exception as e:
                return f"查询执行错误：{str(e)}"

        else:
            return "错误：不支持的action（仅支持list_tables/get_schema/query_data）"