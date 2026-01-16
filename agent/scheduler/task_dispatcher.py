from typing import Dict, Any, List, Type
from datetime import datetime
from mcp.base_mcp import BaseMCP
from mcp.nl2sql.sql_generator import SQLGenerator
from mcp.auto_data_analysis.descriptive_analysis import DescriptiveAnalysis
from mcp.office_parser.excel_parser import ExcelParser
from mcp.python_sandbox.python_sandbox import PythonSandbox
from utils import get_logger, TaskExecuteException

class TaskDispatcher:
    """任务分发器：根据任务类型路由到对应MCP模块，管理模块生命周期"""
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        # 任务类型与MCP模块的映射（核心：实现自动路由）
        self.task_type_to_mcp: Dict[str, Type[BaseMCP]] = {
            "nl2sql": SQLGenerator,
            "auto_data_analysis": DescriptiveAnalysis,
            "office_excel": ExcelParser,
            "python_sandbox": PythonSandbox
        }
        # 已初始化的MCP模块实例缓存（避免重复初始化）
        self.mcp_instances: Dict[str, BaseMCP] = {}

    def dispatch(self, task_dict: Dict[str, Any], mcp_module_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        核心方法：分发单个任务到对应MCP模块
        :param task_dict: 标准化任务字典（从Task结构化对象转换而来）
        :param mcp_module_config: MCP模块专属配置
        :return: MCP模块执行结果
        """
        if not task_dict:
            raise TaskExecuteException("任务字典不能为空")

        # 1. 提取核心任务信息
        task_id = task_dict.get("task_id", "unknown_task")
        task_type = task_dict.get("task_type", "unknown_type")

        # 2. 校验任务类型是否支持
        if task_type not in self.task_type_to_mcp:
            raise TaskExecuteException(f"不支持的任务类型：{task_type}，支持类型：{list(self.task_type_to_mcp.keys())}")

        try:
            # 3. 获取/初始化MCP模块实例
            mcp_instance = self._get_or_init_mcp_instance(task_type, mcp_module_config or {})

            # 4. 执行MCP任务
            self.logger.info(f"开始分发任务 {task_id}（类型：{task_type}）到MCP模块：{mcp_instance.__class__.__name__}")
            mcp_result = mcp_instance.execute(task_dict)

            self.logger.info(f"任务 {task_id} 分发执行完成，状态：{mcp_result.get('status')}")
            return mcp_result
        except Exception as e:
            self.logger.error(f"任务 {task_id} 分发执行失败：{str(e)}")
            raise TaskExecuteException(f"任务 {task_id} 分发失败：{str(e)}") from e

    def dispatch_series(self, task_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分发串联任务（多任务按顺序执行，前一个任务结果作为后一个任务输入）
        :param task_list: 标准化任务字典列表
        :return: 所有任务执行结果列表
        """
        if not task_list:
            raise TaskExecuteException("串联任务列表不能为空")

        result_list = []
        prev_task_result = {}  # 前一个任务的执行结果

        for idx, task_dict in enumerate(task_list):
            task_id = task_dict.get("task_id", f"unknown_task_{idx}")
            try:
                # 补充前一个任务结果到当前任务参数（实现串联）
                task_dict["params"]["prev_task_result"] = prev_task_result

                # 分发当前任务
                current_result = self.dispatch(task_dict)
                result_list.append(current_result)

                # 更新前一个任务结果（仅保存成功的结果）
                if current_result.get("status") == "success":
                    prev_task_result = current_result

                self.logger.info(f"串联任务 {idx+1}/{len(task_list)}（{task_id}）执行完成")
            except Exception as e:
                self.logger.error(f"串联任务 {idx+1}/{len(task_list)}（{task_id}）执行失败：{str(e)}")
                result_list.append({
                    "task_id": task_id,
                    "status": "failed",
                    "error_msg": str(e),
                    "execute_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                # 可选：是否终止串联任务（此处选择继续执行后续任务）

        return result_list

    def _get_or_init_mcp_instance(self, task_type: str, module_config: Dict[str, Any]) -> BaseMCP:
        """获取或初始化MCP模块实例（缓存实例，避免重复初始化）"""
        if task_type in self.mcp_instances:
            return self.mcp_instances[task_type]

        # 初始化MCP模块
        mcp_class = self.task_type_to_mcp[task_type]
        mcp_instance = mcp_class()
        init_success = mcp_instance.init(module_config)

        if not init_success:
            raise TaskExecuteException(f"MCP模块 {mcp_class.__name__} 初始化失败")

        # 缓存实例
        self.mcp_instances[task_type] = mcp_instance
        return mcp_instance

    def close_all_mcp_instances(self) -> None:
        """关闭所有已初始化的MCP模块实例，释放资源"""
        self.logger.info("开始关闭所有MCP模块实例...")
        for task_type, mcp_instance in self.mcp_instances.items():
            try:
                mcp_instance.close()
                self.logger.info(f"MCP模块 {task_type} 关闭成功")
            except Exception as e:
                self.logger.error(f"MCP模块 {task_type} 关闭失败：{str(e)}")
        self.mcp_instances.clear()
        self.logger.info("所有MCP模块实例关闭完成")