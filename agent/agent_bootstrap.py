"""
Agent 全局引导类：统一初始化所有模块，提供对话入口，管理资源生命周期
是整个 AI Report Agent 的对外统一接口，简化使用流程
"""
from typing import Optional, Dict, Any, List
from datetime import datetime

# 导入配置模块
from config import (
    get_global_config,
    get_llm_config,
    get_scenario_widetable_mapping
)

# 导入 Agent 核心模块
from agent.core import BaseAgent, ReportAgent
from agent.dialogue import ContextManager, MemoryStore
from agent.parser import NLParser, TaskStructor, ScenarioMatcher
from agent.scheduler.task_dispatcher import TaskDispatcher
from agent.scheduler.result_assembler import ResultAssembler
from agent.llm import DeepSeekLLM

# 导入 MCP 模块
from mcp.base_mcp import BaseMCP

# 导入工具模块
from utils import (
    get_logger,
    ensure_dir,
    TaskExecuteException,
    ConfigException,
    FileOperateException
)


class AIReportAgent:
    """AI 报表 Agent 全局类：统一封装初始化、对话、资源释放"""

    def __init__(self):
        # 1. 基础属性初始化
        self.logger = get_logger(self.__class__.__name__)
        self.initialized = False  # Agent 初始化就绪标记
        self.global_config: Dict[str, Any] = {}
        self.llm_config: Dict[str, Any] = {}
        self.scenario_mapping: Dict[str, Any] = {}

        # 2. 模块实例缓存（所有核心模块实例）
        self.llm_instance: Optional[DeepSeekLLM] = None
        self.context_manager: Optional[ContextManager] = None
        self.memory_store: Optional[MemoryStore] = None
        self.nl_parser: Optional[NLParser] = None
        self.task_structor: Optional[TaskStructor] = None
        self.scenario_matcher: Optional[ScenarioMatcher] = None
        self.task_dispatcher: Optional[TaskDispatcher] = None
        self.result_assembler: Optional[ResultAssembler] = None
        self.report_agent: Optional[ReportAgent] = None

        # 3. 路径初始化（确保必要目录存在）
        self._init_required_dirs()

    def _init_required_dirs(self) -> None:
        """初始化项目必要目录（输出、临时、日志等，避免文件操作异常）"""
        try:
            # 先加载全局配置（仅路径部分）
            temp_global_config = get_global_config()
            path_config = temp_global_config.get("path", {})
            for dir_path in path_config.values():
                ensure_dir(dir_path)
            self.logger.info("项目必要目录初始化完成")
        except Exception as e:
            raise FileOperateException(f"初始化必要目录失败：{str(e)}")

    def init(self) -> bool:
        """
        核心方法：全局初始化所有模块（按顺序加载，确保依赖正确）
        :return: 初始化是否成功
        """
        if self.initialized:
            self.logger.warning("Agent 已初始化，无需重复执行")
            return True

        try:
            self.logger.info("开始初始化 AI Report Agent 所有模块...")

            # 步骤1：加载所有配置（单例缓存，无需重复加载）
            self._load_all_configs()

            # 步骤2：初始化 LLM 实例（DeepSeek）
            self._init_llm()

            # 步骤3：初始化对话管理模块（上下文+记忆）
            self._init_dialogue_modules()

            # 步骤4：初始化指令解析模块（NL解析+任务结构化+场景匹配）
            self._init_parser_modules()

            # 步骤5：初始化任务调度与结果整合模块
            self._init_scheduler_modules()

            # 步骤6：初始化报表专属 Agent
            self._init_report_agent()

            # 步骤7：标记初始化完成
            self.initialized = True
            self.logger.info("AI Report Agent 所有模块初始化成功，就绪可用")
            return True

        except (ConfigException, TaskExecuteException, FileOperateException) as e:
            self.logger.error(f"Agent 初始化失败：{str(e)}")
            self.close()  # 初始化失败，释放已加载资源
            return False
        except Exception as e:
            self.logger.error(f"Agent 初始化未知异常：{str(e)}")
            self.close()
            return False

    def _load_all_configs(self) -> None:
        """加载所有配置文件（全局、LLM、场景映射）"""
        self.logger.info("加载项目配置文件...")
        self.global_config = get_global_config()
        self.llm_config = get_llm_config()
        self.scenario_mapping = get_scenario_widetable_mapping()

        # 验证核心配置是否存在
        if not self.global_config:
            raise ConfigException("全局配置加载失败，配置为空")
        if not self.llm_config.get("deepseek"):
            raise ConfigException("DeepSeek LLM 配置加载失败")
        if not self.scenario_mapping.get("scene_widetable_mapping"):
            raise ConfigException("场景-宽表映射配置加载失败")

    def _init_llm(self) -> None:
        """初始化 LLM 实例（DeepSeek）"""
        self.logger.info("初始化 DeepSeek LLM 实例...")
        self.llm_instance = DeepSeekLLM()
        self.logger.info("DeepSeek LLM 实例初始化成功")

    def _init_dialogue_modules(self) -> None:
        """初始化对话管理模块（上下文管理器 + 记忆存储）"""
        self.logger.info("初始化对话管理模块...")
        agent_config = self.global_config.get("agent", {})

        # 初始化上下文管理器
        self.context_manager = ContextManager(
            max_context_length=agent_config.get("context_max_length", 5000)
        )

        # 初始化记忆存储
        self.memory_store = MemoryStore(
            long_memory_keep_count=agent_config.get("long_memory_keep_count", 10)
        )
        self.logger.info("对话管理模块初始化成功")

    def _init_parser_modules(self) -> None:
        """初始化指令解析模块（NL解析 + 任务结构化 + 场景匹配）"""
        self.logger.info("初始化指令解析模块...")

        # 初始化 NL 解析器（依赖 LLM 实例）
        self.nl_parser = NLParser(
            llm=self.llm_instance,
            default_scene=self.global_config.get("agent", {}).get("default_scene", "成本分析")
        )

        # 初始化任务结构化器
        self.task_structor = TaskStructor()

        # 初始化场景匹配器（依赖场景映射配置）
        self.scenario_matcher = ScenarioMatcher(
            scene_widetable_mapping=self.scenario_mapping["scene_widetable_mapping"]
        )
        self.logger.info("指令解析模块初始化成功")

    def _init_scheduler_modules(self) -> None:
        """初始化任务调度与结果整合模块"""
        self.logger.info("初始化任务调度与结果整合模块...")

        # 初始化任务分发器（管理 MCP 模块生命周期）
        self.task_dispatcher = TaskDispatcher()

        # 初始化结果整合器
        self.result_assembler = ResultAssembler()
        self.logger.info("任务调度与结果整合模块初始化成功")

    def _init_report_agent(self) -> None:
        """初始化报表专属 Agent（继承 BaseAgent，实现金融报表业务）"""
        self.logger.info("初始化报表专属 Agent...")
        self.report_agent = ReportAgent(
            context_manager=self.context_manager,
            memory_store=self.memory_store,
            nl_parser=self.nl_parser,
            task_structor=self.task_structor,
            scenario_matcher=self.scenario_matcher,
            task_dispatcher=self.task_dispatcher,
            result_assembler=self.result_assembler
        )
        self.logger.info("报表专属 Agent 初始化成功")

    def chat(self, user_input: str) -> str:
        """
        核心对话方法：接收用户自然语言输入，返回格式化回复
        :param user_input: 用户自然语言输入（如"查询2024年2月成本数据并生成Excel报表"）
        :return: Agent 格式化回复（包含执行结果、文件路径等）
        """
        if not self.initialized:
            raise TaskExecuteException("Agent 未初始化就绪，请先调用 init() 方法")

        if not user_input or not user_input.strip():
            return "❌ 输入不能为空，请提供有效的业务需求。"

        try:
            self.logger.info(f"接收用户输入：{user_input}")
            start_time = datetime.now()

            # 步骤1：补充上下文（将用户输入加入上下文）
            self.context_manager.add_user_message(user_input)

            # 步骤2：调用报表 Agent 处理核心业务（全链路处理）
            task_result = self.report_agent.process_task(user_input)

            # 步骤3：整合结果，生成格式化回复
            formatted_reply = self._format_reply(task_result)

            # 步骤4：更新上下文和长期记忆
            self.context_manager.add_agent_message(formatted_reply)
            self.memory_store.add_long_memory({
                "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "user_input": user_input,
                "agent_reply": formatted_reply,
                "task_id": task_result.get("task_id", "unknown"),
                "status": task_result.get("status", "failed")
            })

            # 步骤5：打印耗时信息
            cost_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"用户任务处理完成，耗时：{cost_time:.2f} 秒")

            return formatted_reply

        except TaskExecuteException as e:
            error_msg = f"❌ 任务执行失败：{str(e)}"
            self.logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"❌ 未知错误：{str(e)}"
            self.logger.error(error_msg)
            return error_msg

    def _format_reply(self, task_result: Dict[str, Any]) -> str:
        """格式化任务结果，生成友好的用户回复"""
        if not task_result:
            return "❌ 任务处理结果为空。"

        status = task_result.get("status", "failed")
        if status != "success":
            return f"❌ 任务执行失败：{task_result.get('error_msg', '未知错误')}"

        # 提取核心结果字段
        task_id = task_result.get("task_id", "unknown")
        mcp_module = task_result.get("mcp_module", "未知模块")
        final_report_path = task_result.get("final_report_path", "")
        output_files = task_result.get("output_files", [])
        data_summary = task_result.get("final_data", {})

        # 构建回复内容
        reply = f"✅ 任务执行成功（任务ID：{task_id}）\n"
        reply += f"🔧 执行模块：{mcp_module}\n"

        # 补充数据摘要（简化展示）
        if data_summary:
            if "statistics_result" in data_summary:
                stats = data_summary["statistics_result"]
                reply += f"📊 数据摘要：\n"
                for field, stats_data in stats.items():
                    reply += f"  - {field}：均值 {stats_data.get('mean', 0)}，总和 {stats_data.get('sum', 0)}\n"
            elif "excel_file_path" in data_summary:
                reply += f"📊 数据摘要：Excel 文件已生成，大小 {data_summary.get('file_size', 0)} KB\n"

        # 补充输出文件路径
        if output_files:
            reply += f"📁 生成文件：\n"
            for file_path in output_files[:3]:  # 最多展示3个文件
                reply += f"  - {file_path}\n"
            if len(output_files) > 3:
                reply += f"  - 还有 {len(output_files) - 3} 个文件未展示\n"

        # 补充最终报告
        if final_report_path:
            reply += f"📋 最终报告：{final_report_path}\n"

        reply += "\n💡 所有文件已保存至项目 data/output 目录，可直接打开查看。"
        return reply

    def close(self) -> None:
        """
        释放所有资源（关闭 MCP、LLM、数据库、文件句柄等）
        程序退出前必须调用，避免资源泄漏
        """
        self.logger.info("开始释放 Agent 所有资源...")

        # 1. 关闭任务分发器（统一关闭所有 MCP 实例）
        if self.task_dispatcher:
            self.task_dispatcher.close_all_mcp_instances()

        # 2. 清空上下文和记忆（可选）
        if self.context_manager:
            self.context_manager.clear_context()

        if self.memory_store:
            self.memory_store.clear_short_memory()

        # 3. 标记为未初始化
        self.initialized = False
        self.logger.info("Agent 所有资源释放完成")

    def get_agent_status(self) -> Dict[str, Any]:
        """获取 Agent 当前状态（用于监控和调试）"""
        return {
            "initialized": self.initialized,
            "project_name": self.global_config.get("project", {}).get("name", "unknown"),
            "project_version": self.global_config.get("project", {}).get("version", "unknown"),
            "context_length": len(self.context_manager.get_context()) if self.context_manager else 0,
            "long_memory_count": len(self.memory_store.get_long_memory()) if self.memory_store else 0,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }