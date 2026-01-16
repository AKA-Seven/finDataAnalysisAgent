# ai_report_agent/mcp/base_mcp.py
"""MCP基类：定义所有MCP模块的通用接口与数据流规范"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from ai_report_agent.config import get_global_config
from ai_report_agent.utils import get_logger, AgentBaseException

class BaseMCP(ABC):
    """所有MCP模块的抽象基类，定义统一接口与数据流规范"""
    def __init__(self):
        # 通用配置与日志
        self.global_config = get_global_config()
        self.logger = get_logger(self.__class__.__name__)
        self.initialized = False
        self.module_config: Dict[str, Any] = {}  # 模块专属配置

    @abstractmethod
    def init(self, module_config: Dict[str, Any] = None) -> bool:
        """
        初始化模块（加载配置、创建连接、初始化资源）
        :param module_config: 模块专属配置（覆盖全局配置）
        :return: 初始化是否成功
        """
        pass

    @abstractmethod
    def execute(self, task_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行核心任务（标准化输入输出）
        :param task_dict: 标准化任务字典（从Task结构化对象转换而来）
        :return: 标准化结果字典
        """
        pass

    @abstractmethod
    def close(self) -> bool:
        """释放资源（关闭数据库连接、文件句柄、销毁环境等）"""
        pass

    def _standardize_input(self, task_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        通用输入标准化（补全必填字段，避免KeyError）
        必填字段：task_id、task_type、scene、params、output_path
        """
        required_fields = ["task_id", "task_type", "scene", "params", "output_path"]
        standardized_task = task_dict.copy()

        # 补全缺失必填字段
        for field in required_fields:
            if field not in standardized_task:
                if field == "params":
                    standardized_task[field] = {}
                elif field == "output_path":
                    standardized_task[field] = self.global_config.get("default_output_path", "./data/output")
                else:
                    standardized_task[field] = "unknown"
                    self.logger.warning(f"任务 {standardized_task.get('task_id')} 缺失字段 {field}，已补全为默认值")

        return standardized_task

    def _standardize_output(self, status: str, data: Any = None, error_msg: str = "") -> Dict[str, Any]:
        """
        通用输出标准化（统一结果格式，便于结果整合）
        :param status: 执行状态（success/failed/running）
        :param data: 核心执行结果（任意可序列化数据）
        :param error_msg: 错误信息（仅status=failed时填充）
        :return: 标准化结果字典
        """
        return {
            "mcp_module": self.__class__.__name__,
            "task_id": "",  # 后续由任务分发器填充
            "status": status,
            "data": data or {},
            "error_msg": error_msg,
            "execute_time": "",  # 后续由任务分发器填充（时间戳）
            "output_files": []  # 生成的文件路径列表（便于结果整合）
        }