from typing import Dict, Any
import pandas as pd
from datetime import datetime
from mcp.base_mcp import BaseMCP
from agent.config import get_nl2sql_config

class SQLGenerator(BaseMCP):
    """NL2SQL模块：SQL生成与执行（实现BaseMCP接口）"""
    def __init__(self):
        super().__init__()
        self.sql_verifier = None  # 关联SQL校验器
        self.sql_executor = None  # 关联SQL执行器
        self.table_meta = {}  # 表结构元数据

    def init(self, module_config: Dict[str, Any] = None) -> bool:
        """
        初始化NL2SQL模块（加载表结构、初始化校验器/执行器）
        :param module_config: 专属配置（覆盖nl2sql_config.yaml）
        :return: 初始化是否成功
        """
        try:
            # 加载配置（全局配置 + 自定义配置）
            self.module_config = get_nl2sql_config()
            if module_config:
                self.module_config.update(module_config)

            # 加载表结构元数据
            self.table_meta = self.module_config.get("table_meta", {})
            if not self.table_meta:
                raise Exception("NL2SQL模块缺少表结构元数据")

            # 初始化校验器和执行器（简化实现，实际项目中实例化对应类）
            self.sql_verifier = self._init_verifier()
            self.sql_executor = self._init_executor()

            self.initialized = True
            self.logger.info("NL2SQL模块初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"NL2SQL模块初始化失败：{str(e)}")
            return False

    def execute(self, task_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行NL2SQL任务（标准化输入输出）
        【输入字段】（task_dict["params"]内）：
            - query_demand: 自然语言查询需求（如"查询2024年2月成本数据"）
            - wide_table: 目标宽表名（如"cost_wide_table"）
            - time_range: 查询时间范围（如"2024年2月"）
            - field_mapping: 字段映射（如{"成本金额": "cost_amount"}）
        【输出字段】（result["data"]内）：
            - generated_sql: 生成的合规SQL语句
            - query_result: 查询结果（pandas DataFrame转为列表字典格式）
            - data_count: 数据量
            - field_names: 结果字段名列表
        """
        # 1. 输入标准化
        if not self.initialized:
            return self._standardize_output("failed", error_msg="NL2SQL模块未初始化")
        standardized_task = self._standardize_input(task_dict)
        task_id = standardized_task["task_id"]
        task_params = standardized_task["params"]

        try:
            # 2. 提取专属输入参数
            query_demand = task_params.get("query_demand", "")
            wide_table = task_params.get("wide_table", "")
            time_range = task_params.get("time_range", "")
            field_mapping = task_params.get("field_mapping", {})

            if not (query_demand and wide_table):
                raise Exception("缺少核心查询参数：query_demand/wide_table")

            # 3. 核心逻辑：生成SQL → 校验SQL → 执行SQL（简化实现，模拟结果）
            generated_sql = self._generate_sql(query_demand, wide_table, time_range, field_mapping)
            is_sql_valid = self._verify_sql(generated_sql)
            if not is_sql_valid:
                raise Exception("生成的SQL不符合合规要求，禁止执行")

            query_result, data_count, field_names = self._execute_sql(generated_sql)

            # 4. 构造专属输出数据
            nl2sql_data = {
                "generated_sql": generated_sql,
                "query_result": query_result,
                "data_count": data_count,
                "field_names": field_names,
                "wide_table": wide_table,
                "time_range": time_range
            }

            # 5. 输出标准化（填充任务ID和执行时间）
            result = self._standardize_output("success", data=nl2sql_data)
            result["task_id"] = task_id
            result["execute_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.logger.info(f"NL2SQL任务 {task_id} 执行成功，返回数据量：{data_count}")
            return result
        except Exception as e:
            error_msg = f"NL2SQL任务 {task_id} 执行失败：{str(e)}"
            self.logger.error(error_msg)
            result = self._standardize_output("failed", error_msg=error_msg)
            result["task_id"] = task_id
            return result

    def close(self) -> bool:
        """释放NL2SQL资源（关闭数据库连接、销毁校验器/执行器）"""
        try:
            if self.sql_executor:
                # 模拟关闭数据库连接
                self.logger.info("NL2SQL模块：关闭数据库连接成功")
            self.initialized = False
            self.logger.info("NL2SQL模块资源释放成功")
            return True
        except Exception as e:
            self.logger.error(f"NL2SQL模块资源释放失败：{str(e)}")
            return False

    # 以下为辅助方法（简化实现，实际项目中完善）
    def _init_verifier(self):
        """初始化SQL校验器"""
        self.logger.info("初始化SQL校验器成功")
        return "SQLVerifierInstance"

    def _init_executor(self):
        """初始化SQL执行器"""
        self.logger.info("初始化SQL执行器成功")
        return "SQLExecutorInstance"

    def _generate_sql(self, query_demand: str, wide_table: str, time_range: str, field_mapping: Dict) -> str:
        """模拟生成合规SQL"""
        fields = ",".join(field_mapping.values()) if field_mapping else "*"
        time_field = self.module_config.get("default_time_field", "create_time")
        return f"SELECT {fields} FROM {wide_table} WHERE {time_field} LIKE '%{time_range}%';"

    def _verify_sql(self, sql: str) -> bool:
        """模拟SQL校验（禁止DROP/DELETE等危险操作）"""
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER"]
        return not any(keyword in sql.upper() for keyword in dangerous_keywords)

    def _execute_sql(self, sql: str) -> (list, int, list):
        """模拟执行SQL，返回结果（转为列表字典格式，便于序列化）"""
        # 模拟DataFrame结果
        df = pd.DataFrame({
            "cost_amount": [10000, 20000, 15000],
            "cost_type": ["人力成本", "物料成本", "运营成本"],
            "settle_date": ["2024-02-10", "2024-02-15", "2024-02-20"]
        })
        query_result = df.to_dict("records")
        data_count = len(query_result)
        field_names = df.columns.tolist()
        return query_result, data_count, field_names