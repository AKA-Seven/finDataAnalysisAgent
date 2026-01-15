# agent/parser/task_structor.py
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
import uuid

from agent.parser.nl_parser import NLParser
from agent.dialogue import MemoryStore, ContextManager


@dataclass
class Task:
    """
    结构化任务数据类，定义MCP可执行的统一任务格式
    核心字段：任务ID、任务类型、业务场景、MCP配置、任务参数、优先级、创建时间
    """
    # 必选字段
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])  # 生成8位唯一任务ID
    task_type: str = field(default="auto_analysis")  # 对应MCP模块：nl2sql/auto_analysis/sandbox_execute
    scene: str = field(default="未知场景")  # 业务场景

    # 可选字段
    mcp_config: Dict[str, Any] = field(default_factory=dict)  # MCP模块配置（大模型/数据库等）
    params: Dict[str, Any] = field(default_factory=dict)  # 任务执行参数
    priority: int = field(default=2)  # 优先级：1（高）> 2（中）> 3（低）
    create_time: str = field(default_factory=lambda: str(uuid.uuid1().time_low))  # 简化创建时间
    status: str = field(default="pending")  # 任务状态：pending/running/success/failed

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，供MCP模块直接使用"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "scene": self.scene,
            "mcp_config": self.mcp_config,
            "params": self.params,
            "priority": self.priority,
            "create_time": self.create_time,
            "status": self.status
        }


class TaskStructor:
    """
    任务结构化转换类，将NLParser的原始解析结果转为Task实例
    核心功能：转换结构化任务、补全MCP默认配置、校验任务完整性
    """

    def __init__(self, nl_parser: NLParser):
        """
        初始化任务结构化器（依赖注入NLParser）
        :param nl_parser: 自然语言解析器实例，用于获取原始解析结果
        """
        self._nl_parser = nl_parser
        # MCP模块映射（任务类型 → MCP模块）
        self._task_type_to_mcp = {
            "nl2sql": "NL2PythonDFMCP",
            "auto_analysis": "AutoDataAnalysisMCP",
            "sandbox_execute": "SafePythonSandbox"
        }
        # 默认MCP配置（兜底，可被外部覆盖）
        self._default_mcp_config = {
            "llm_api_config": {
                "api_key": "",
                "base_url": "https://api.deepseek.com",
                "model_name": "deepseek-chat",
                "max_tokens": 3000,
                "temperature": 0.1
            },
            "db_config": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "",
                "db": "business_analysis_db",
                "charset": "utf8mb4"
            }
        }

    def convert_to_task(self, custom_mcp_config: Optional[Dict] = None) -> Task:
        """
        核心方法：将原始解析结果转为结构化Task实例
        :param custom_mcp_config: 自定义MCP配置，优先于默认配置
        :return: 结构化Task实例
        """
        # 1. 获取原始解析结果并校验
        parse_result = self._nl_parser.parse_nl()
        is_valid, error_msg = self._nl_parser.validate_parse_result(parse_result)
        if not is_valid:
            raise Exception(f"原始解析结果无效，无法转换为任务：{error_msg}")

        # 2. 确定任务类型（根据操作类型映射）
        task_type = self._map_operation_to_task_type(parse_result.get("operation", ""))

        # 3. 补全MCP配置（自定义配置优先于默认配置）
        mcp_config = self._default_mcp_config.copy()
        if custom_mcp_config:
            mcp_config.update(custom_mcp_config)

        # 4. 构建任务参数
        task_params = {
            "time_range": parse_result.get("time_range"),
            "data_type": parse_result.get("data_type"),
            "operation": parse_result.get("operation"),
            "target": parse_result.get("target"),
            "raw_input": parse_result.get("raw_input")
        }

        # 5. 生成结构化Task实例
        task = Task(
            task_type=task_type,
            scene=parse_result.get("scene", "未知场景"),
            mcp_config=mcp_config,
            params=task_params
        )

        return task

    def _map_operation_to_task_type(self, operation: str) -> str:
        """将操作类型映射为任务类型（对应MCP模块）"""
        operation_to_task_type = {
            "统计聚合": "nl2sql",
            "趋势分析": "auto_analysis",
            "报表生成": "auto_analysis",
            "异常识别": "auto_analysis"
        }
        return operation_to_task_type.get(operation, "auto_analysis")  # 默认auto_analysis

    def validate_task(self, task: Task) -> (bool, Optional[str]):
        """
        校验结构化Task的完整性
        :param task: 结构化Task实例
        :return: （是否有效，错误信息/None）
        """
        # 1. 必选字段校验
        if not task.task_type or task.task_type not in self._task_type_to_mcp:
            return False, f"无效任务类型：{task.task_type}，支持类型：{list(self._task_type_to_mcp.keys())}"

        if task.scene in ["未知场景", ""]:
            return False, "任务缺少有效业务场景"

        # 2. MCP配置校验（至少包含大模型配置）
        if not task.mcp_config.get("llm_api_config"):
            return False, "任务缺少有效MCP大模型配置"

        return True, None

    def format_task_for_mcp(self, task: Task) -> Dict[str, Any]:
        """将Task实例格式化为MCP模块可直接接收的参数格式"""
        if not self.validate_task(task)[0]:
            raise Exception("任务无效，无法格式化为MCP输入参数")

        return task.to_dict()


# 测试示例（可直接运行该文件验证功能）
if __name__ == "__main__":
    # 1. 初始化前置模块（记忆存储→上下文管理器→自然语言解析器）
    memory = MemoryStore()
    context_manager = ContextManager(memory)
    user_input = "帮我统计2024年2月的销售数据，生成Excel报表"
    context_manager.update_context(user_input)
    nl_parser = NLParser(context_manager)

    # 2. 初始化任务结构化器
    task_structor = TaskStructor(nl_parser)

    # 3. 转换为结构化任务
    try:
        task = task_structor.convert_to_task()
        is_task_valid, task_error = task_structor.validate_task(task)

        print("=== 结构化Task结果 ===")
        print(f"任务ID：{task.task_id}")
        print(f"任务类型：{task.task_type}")
        print(f"业务场景：{task.scene}")
        print(f"任务参数：{task.params}")
        print(f"任务状态：{task.status}")

        print(f"\n=== Task转MCP可用字典 ===")
        import pprint

        pprint.pprint(task.to_dict())

        print(f"\n=== 任务校验结果 ===")
        print(f"是否有效：{is_task_valid}")
        if not is_task_valid:
            print(f"错误信息：{task_error}")
    except Exception as e:
        print(f"任务转换失败：{e}")