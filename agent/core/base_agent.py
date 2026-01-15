# agent/core/base_agent.py
import abc
from typing import Dict, Optional, Any, Tuple
from dataclasses import asdict

# 统一绝对导入：依赖前两阶段的核心模块
from agent.dialogue import MemoryStore, ContextManager
from agent.parser import NLParser, TaskStructor, ScenarioMatcher, Task


class BaseAgent(abc.ABC):
    """
    Agent抽象基类，定义通用核心流程和抽象接口
    通用方法：对话初始化、接收用户输入、指令解析、记忆管理、结果格式化
    抽象接口：任务执行、业务场景适配（由子类实现专属逻辑）
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
        初始化Agent基类（依赖注入所有前置模块，提升灵活性和可测试性）
        :param memory_store: 记忆存储实例
        :param context_manager: 上下文管理实例
        :param nl_parser: 自然语言解析实例
        :param task_structor: 任务结构化转换实例
        :param scenario_matcher: 场景匹配实例
        """
        self._memory = memory_store
        self._context = context_manager
        self._nl_parser = nl_parser
        self._task_structor = task_structor
        self._scenario_matcher = scenario_matcher

        # 初始化对话状态
        self._dialogue_initialized = False
        self._current_task: Optional[Task] = None
        self._latest_result: Optional[Dict[str, Any]] = None

    def init_dialogue(self, clear_expired_long_memory: bool = True) -> None:
        """
        通用方法：初始化对话，准备接收用户输入
        :param clear_expired_long_memory: 是否清理过期长期记忆（默认True，保留最新10条）
        """
        # 清理过期长期记忆
        if clear_expired_long_memory:
            self._memory.clear_expired_long_term_memory(keep_latest_n=10)

        # 清空当前短期记忆
        self._memory.clear_short_term_memory()

        # 更新对话状态
        self._dialogue_initialized = True
        self._current_task = None
        self._latest_result = None

        print("=== 对话初始化完成，可接收用户输入 ===")

    def receive_user_input(self, user_input: str) -> bool:
        """
        通用方法：接收用户输入，更新对话上下文
        :param user_input: 用户自然语言输入
        :return: 是否接收成功（对话已初始化且输入有效返回True）
        """
        # 校验对话状态和输入有效性
        if not self._dialogue_initialized:
            print("错误：对话未初始化，请先调用init_dialogue()方法")
            return False
        if not user_input or not user_input.strip():
            print("错误：无效用户输入，不能为空")
            return False

        # 更新上下文（自动清理上一轮短期记忆）
        self._context.update_context(user_input.strip())
        print("=== 用户输入已接收，上下文已更新 ===")
        return True

    def parse_instruction(self, custom_mcp_config: Optional[Dict] = None) -> Optional[Task]:
        """
        通用方法：解析用户指令，生成补全场景的结构化Task
        :param custom_mcp_config: 自定义MCP配置，覆盖默认配置
        :return: 补全场景信息的结构化Task实例，失败返回None
        """
        if not self._dialogue_initialized:
            print("错误：对话未初始化，无法解析指令")
            return None

        try:
            # 1. 自然语言解析
            parse_result = self._nl_parser.parse_nl()
            is_valid, error_msg = self._nl_parser.validate_parse_result(parse_result)
            if not is_valid:
                raise Exception(f"指令解析失败：{error_msg}")

            # 2. 转换为结构化Task
            task = self._task_structor.convert_to_task(custom_mcp_config)
            is_task_valid, task_error = self._task_structor.validate_task(task)
            if not is_task_valid:
                raise Exception(f"任务结构化失败：{task_error}")

            # 3. 场景匹配，补全宽表和处理规则
            self._current_task = self._scenario_matcher.match_scene_to_table(task)
            print("=== 指令解析完成，生成结构化Task ===")
            return self._current_task

        except Exception as e:
            print(f"=== 指令解析异常：{e} ===")
            return None

    def manage_memory(self, save_to_long_term: bool = True) -> None:
        """
        通用方法：统一管理记忆（更新短期记忆，可选保存到长期记忆）
        :param save_to_long_term: 是否将当前任务结果保存到长期记忆（默认True）
        """
        if not self._dialogue_initialized:
            print("错误：对话未初始化，无法管理记忆")
            return

        # 1. 更新短期记忆（保存当前任务）
        if self._current_task:
            self._memory.add_short_term_memory(
                key="current_task",
                value=self._current_task.to_dict()
            )

        # 2. 保存到长期记忆（若有最新结果且开启保存）
        if save_to_long_term and self._latest_result:
            scene = self._current_task.scene if self._current_task else "未知场景"
            self._memory.add_long_term_memory(
                scene=scene,
                result=self._latest_result,
                task_id=self._current_task.task_id if self._current_task else "未知任务ID",
                time_range=self._current_task.params.get("time_range", "未指定时间") if self._current_task else "未指定时间"
            )
            print("=== 记忆管理完成，当前结果已保存到长期记忆 ===")
        else:
            print("=== 记忆管理完成，仅更新短期记忆 ===")

    def format_result(self, result: Optional[Dict] = None) -> str:
        """
        通用方法：格式化结果，返回人类可读的文本格式
        :param result: 待格式化的结果字典，默认使用最新结果
        :return: 格式化后的文本结果
        """
        target_result = result or self._latest_result
        if not target_result:
            return "暂无有效结果可展示"

        # 通用格式化逻辑（可被子类重写，适配专属场景）
        format_parts = ["=== Agent执行结果 ==="]
        format_parts.append(f"业务场景：{target_result.get('scene', '未知场景')}")
        format_parts.append(f"任务ID：{target_result.get('task_id', '未知任务ID')}")
        format_parts.append(f"执行状态：{target_result.get('status', '未知状态')}")
        format_parts.append(f"核心结论：{target_result.get('conclusion', '无核心结论')}")
        format_parts.append(f"输出路径：{target_result.get('export_path', '未生成文件')}")

        return "\n".join(format_parts)

    @abc.abstractmethod
    def _execute_task(self) -> Optional[Dict[str, Any]]:
        """
        抽象方法：执行任务（由子类实现专属业务逻辑，如调用调度模块、对接MCP）
        :return: 任务执行结果字典，失败返回None
        """
        pass

    @abc.abstractmethod
    def _adapt_business_scene(self) -> bool:
        """
        抽象方法：业务场景适配（由子类实现专属场景校验和适配，如金融数据合法性校验）
        :return: 场景适配是否成功
        """
        pass