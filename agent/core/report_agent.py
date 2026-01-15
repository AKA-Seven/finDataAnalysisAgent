# agent/core/report_agent.py
from typing import Dict, Optional, Any, List
import os
from datetime import datetime

# 统一绝对导入：基类和前置模块
from agent.core.base_agent import BaseAgent
from agent.dialogue import MemoryStore, ContextManager
from agent.parser import NLParser, TaskStructor, ScenarioMatcher
from agent.parser import Task

class ReportAgent(BaseAgent):
    """
    报表分析专属Agent，继承BaseAgent，适配金融报表业务场景
    核心功能：实现任务执行、金融场景适配、生成金融报表、校验报表数据、导出Excel/CSV报表
    """
    def __init__(
        self,
        memory_store: MemoryStore,
        context_manager: ContextManager,
        nl_parser: NLParser,
        task_structor: TaskStructor,
        scenario_matcher: ScenarioMatcher
    ):
        """
        初始化报表Agent（调用父类构造函数，注入依赖）
        :param memory_store: 记忆存储实例
        :param context_manager: 上下文管理实例
        :param nl_parser: 自然语言解析实例
        :param task_structor: 任务结构化转换实例
        :param scenario_matcher: 场景匹配实例
        """
        super().__init__(
            memory_store=memory_store,
            context_manager=context_manager,
            nl_parser=nl_parser,
            task_structor=task_structor,
            scenario_matcher=scenario_matcher
        )

        # 金融报表配置
        self._report_export_dir = "./reports"  # 报表导出目录
        self._supported_report_formats = ["xlsx", "csv"]  # 支持的导出格式
        self._financial_field_check = ["金额", "销售额", "成本", "利润", "比率"]  # 金融字段校验列表

    def _adapt_business_scene(self) -> bool:
        """
        实现抽象方法：金融业务场景适配（校验金融数据合法性、场景规则适配）
        :return: 场景适配是否成功
        """
        if not self._current_task:
            print("错误：无当前任务，无法进行场景适配")
            return False

        scene = self._current_task.scene
        task_params = self._current_task.params

        try:
            # 1. 校验金融场景支持性
            supported_financial_scenes = ["销售分析", "成本分析", "利润分析", "异常检测"]
            if scene not in supported_financial_scenes:
                raise Exception(f"不支持的金融场景：{scene}，支持场景：{supported_financial_scenes}")

            # 2. 校验核心金融字段（从字段映射中提取）
            field_mapping = task_params.get("field_mapping", {})
            financial_field_exists = any(field in field_mapping for field in self._financial_field_check)
            if not financial_field_exists:
                raise Exception(f"任务缺少有效金融字段，无法生成合规报表")

            # 3. 适配场景专属规则（如成本分析必须包含异常检测）
            if scene == "成本分析" and "异常检测" not in task_params.get("process_rules", []):
                task_params["process_rules"].append("补充成本异常检测（金融合规要求）")

            print(f"=== 金融场景适配完成：{scene}，符合合规要求 ===")
            return True

        except Exception as e:
            print(f"=== 金融场景适配失败：{e} ===")
            return False

    def _execute_task(self) -> Optional[Dict[str, Any]]:
        """
        实现抽象方法：执行金融报表任务（模拟对接MCP模块，生成报表结果）
        :return: 任务执行结果字典，失败返回None
        """
        if not self._current_task or not self._adapt_business_scene():
            return None

        try:
            scene = self._current_task.scene
            task_id = self._current_task.task_id
            task_params = self._current_task.params

            # 模拟对接MCP模块执行任务（实际项目中替换为真实MCP调用）
            print(f"=== 开始执行金融报表任务：{task_id}（场景：{scene}）===")
            print(f"=== 正在调用MCP模块，执行处理规则 ===")
            for idx, rule in enumerate(task_params.get("process_rules", []), 1):
                print(f"  {idx}. 执行规则：{rule}")

            # 生成模拟报表结果（实际项目中替换为MCP返回的真实结果）
            report_result = {
                "task_id": task_id,
                "scene": scene,
                "status": "success",
                "time_range": task_params.get("time_range", "未指定时间"),
                "wide_table": task_params.get("wide_table", "未知宽表"),
                "conclusion": f"{scene}完成：{task_params.get('time_range')}数据已统计，符合金融合规要求，异常数据（如有）已标注",
                "process_rules_executed": task_params.get("process_rules", []),
                "data_count": 1000 + (hash(task_id) % 9000),  # 模拟数据量
                "export_path": None
            }

            # 生成报表文件（模拟导出）
            export_path = self.generate_financial_report(report_result)
            if export_path:
                report_result["export_path"] = export_path

            # 校验报表数据
            if self.verify_report_data(report_result):
                self._latest_result = report_result
                print(f"=== 金融报表任务执行完成：{task_id} ===")
                return self._latest_result
            else:
                raise Exception("报表数据校验失败，任务执行终止")

        except Exception as e:
            print(f"=== 金融报表任务执行失败：{e} ===")
            return None

    def generate_financial_report(self, report_result: Dict[str, Any], format: str = "xlsx") -> Optional[str]:
        """
        金融报表专属方法：生成金融合规报表（模拟Excel/CSV文件导出）
        :param report_result: 报表结果字典
        :param format: 报表格式（支持xlsx/csv）
        :return: 报表文件路径，失败返回None
        """
        if format not in self._supported_report_formats:
            print(f"错误：不支持的报表格式：{format}，支持格式：{self._supported_report_formats}")
            return None

        try:
            # 1. 创建报表导出目录（不存在则创建）
            os.makedirs(self._report_export_dir, exist_ok=True)

            # 2. 构造报表文件名
            scene = report_result.get("scene", "未知场景").replace(" ", "_")
            time_range = report_result.get("time_range", "未知时间").replace(" ", "_").replace("/", "-").replace("\\", "-")
            task_id = report_result.get("task_id", "未知任务ID")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{scene}_{time_range}_{task_id}_{timestamp}.{format}"
            file_path = os.path.abspath(os.path.join(self._report_export_dir, filename))

            # 3. 模拟生成报表文件（实际项目中使用openpyxl/pandas生成真实文件）
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("=== 金融合规报表 ===\n")
                for key, value in report_result.items():
                    if key != "process_rules_executed":
                        f.write(f"{key}：{value}\n")
                    else:
                        f.write(f"{key}：\n")
                        for idx, rule in enumerate(value, 1):
                            f.write(f"  {idx}. {rule}\n")

            print(f"=== 金融报表生成完成：{file_path} ===")
            return file_path

        except Exception as e:
            print(f"=== 金融报表生成失败：{e} ===")
            return None

    def verify_report_data(self, report_result: Dict[str, Any]) -> bool:
        """
        金融报表专属方法：校验报表数据合法性（金融场景特殊校验）
        :param report_result: 报表结果字典
        :return: 校验是否通过
        """
        try:
            # 1. 核心字段校验
            required_fields = ["task_id", "scene", "status", "conclusion"]
            missing_fields = [f for f in required_fields if f not in report_result]
            if missing_fields:
                raise Exception(f"缺失核心报表字段：{missing_fields}")

            # 2. 状态校验
            if report_result.get("status") != "success":
                raise Exception(f"报表执行状态异常：{report_result.get('status')}")

            # 3. 金融数据量校验（模拟：数据量需大于0）
            data_count = report_result.get("data_count", 0)
            if data_count <= 0:
                raise Exception(f"报表数据量异常：{data_count}（需大于0）")

            # 4. 合规结论校验
            conclusion = report_result.get("conclusion", "")
            if "金融合规" not in conclusion and report_result.get("scene") in ["成本分析", "利润分析"]:
                raise Exception(f"报表结论缺少金融合规声明：{conclusion}")

            print("=== 报表数据校验完成，符合金融合规要求 ===")
            return True

        except Exception as e:
            print(f"=== 报表数据校验失败：{e} ===")
            return False

    def export_report(self, report_result: Optional[Dict] = None, format: str = "xlsx") -> Optional[str]:
        """
        金融报表专属方法：导出报表（复用generate_financial_report，简化外部调用）
        :param report_result: 报表结果字典，默认使用最新结果
        :param format: 报表格式
        :return: 报表文件路径
        """
        target_result = report_result or self._latest_result
        if not target_result:
            print("错误：无有效报表结果可导出")
            return None

        return self.generate_financial_report(target_result, format)