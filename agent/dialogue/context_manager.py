# agent/dialogue/context_manager.py
from typing import Dict, List, Optional, Any
from agent.dialogue.memory_store import MemoryStore


class ContextManager:
    """
    对话上下文管理类，依赖MemoryStore，负责整合「历史记忆+当前输入」，提取关键上下文信息
    核心功能：更新上下文、获取完整上下文、提取关键信息、校验上下文完整性
    """

    def __init__(self, memory_store: MemoryStore):
        """
        初始化上下文管理器（依赖注入MemoryStore，提升灵活性）
        :param memory_store: MemoryStore实例，用于获取/更新对话记忆
        """
        self._memory = memory_store
        # 关键上下文字段（可根据业务扩展）
        self._core_context_fields = ["scene", "time_range", "data_type", "operation"]

    def update_context(self, user_input: str, clear_prev_short: bool = True) -> None:
        """
        更新对话上下文，将新用户输入存入短期记忆，并关联长期记忆补全上下文
        :param user_input: 用户最新输入的自然语言指令
        :param clear_prev_short: 是否清理上一轮的短期记忆（默认True，保证短期记忆仅存储当前轮次）
        """
        # 1. 清理上一轮短期记忆（可选）
        if clear_prev_short:
            self._memory.clear_short_term_memory()

        # 2. 将最新用户输入存入短期记忆
        self._memory.add_short_term_memory("current_user_input", user_input.strip())

        # 3. 关联长期记忆，补全上下文（如当前输入未提及场景，从长期记忆中提取最新场景）
        self._complement_context_from_long_term()

    def _complement_context_from_long_term(self) -> None:
        """从长期记忆中补全当前上下文缺失的关键信息（私有方法，内部调用）"""
        current_input = self._memory.get_short_term_memory("current_user_input")
        if not current_input:
            return

        # 提取长期记忆中最新的业务场景（示例：补全场景信息）
        latest_long_term = self._memory.get_long_term_memory(latest_only=True)
        if latest_long_term and "scene" in latest_long_term:
            # 若当前输入未提及场景，将长期记忆的最新场景存入短期记忆
            if "scene" not in current_input.lower() and not self._memory.get_short_term_memory("scene"):
                self._memory.add_short_term_memory("scene", latest_long_term["scene"])

        # 可扩展：补全时间范围、数据类型等其他关键信息
        if latest_long_term and "time_range" in latest_long_term:
            if "time" not in current_input.lower() and not self._memory.get_short_term_memory("time_range"):
                self._memory.add_short_term_memory("time_range", latest_long_term["time_range"])

    def get_full_context(self, format_for_parser: bool = True) -> str:
        """
        获取完整的对话上下文（历史长期记忆+当前短期记忆）
        :param format_for_parser: 是否格式化上下文（供指令解析模块使用，默认True）
        :return: 完整的对话上下文文本
        """
        # 1. 获取当前短期记忆
        short_term = self._memory.get_short_term_memory()
        if not short_term:
            return "无有效对话上下文"

        # 2. 获取历史长期记忆（最新3条，避免上下文过长）
        long_term = self._memory.get_long_term_memory()[-3:] if self._memory.get_long_term_memory() else []

        # 3. 格式化上下文（便于指令解析模块处理）
        if not format_for_parser:
            return f"长期记忆：{long_term} | 当前输入：{short_term}"

        # 格式化输出示例（清晰区分历史记忆和当前输入）
        context_parts = ["=== 对话上下文 ==="]
        if long_term:
            context_parts.append("### 历史业务记忆（最新3条）")
            for idx, item in enumerate(long_term, 1):
                scene = item.get("scene", "未知场景")
                result = item.get("result", "无结果")
                time = item.get("create_time", "未知时间")
                context_parts.append(f"{idx}. 场景：{scene} | 结果：{result} | 时间：{time}")

        context_parts.append("### 当前用户输入")
        context_parts.append(short_term.get("current_user_input", "无"))

        context_parts.append("### 补全的关键信息")
        for field in self._core_context_fields:
            value = short_term.get(field, "未提及")
            context_parts.append(f"{field}：{value}")

        return "\n".join(context_parts)

    def extract_key_context(self) -> Dict[str, Any]:
        """
        提取关键上下文信息（核心字段），供后续指令解析模块使用
        :return: 关键上下文字典（如{"scene": "销售分析", "time_range": "2024年2月"}）
        """
        short_term = self._memory.get_short_term_memory()
        key_context = {}

        for field in self._core_context_fields:
            # 优先从短期记忆中提取，无则返回"未提及"
            key_context[field] = short_term.get(field, "未提及")

        # 补充当前用户输入到关键上下文
        key_context["current_user_input"] = short_term.get("current_user_input", "未提及")

        return key_context

    def validate_context(self, required_fields: Optional[List[str]] = None) -> (bool, List[str]):
        """
        校验上下文的完整性，检查必要字段是否缺失
        :param required_fields: 必需字段列表；若为None，使用默认核心字段
        :return: （是否完整，缺失的字段列表）
        """
        if required_fields is None:
            required_fields = self._core_context_fields

        key_context = self.extract_key_context()
        missing_fields = []

        for field in required_fields:
            if key_context.get(field, "未提及") == "未提及":
                missing_fields.append(field)

        return (len(missing_fields) == 0, missing_fields)


# 测试示例（可直接运行该文件验证功能）
if __name__ == "__main__":
    # 1. 初始化记忆存储和上下文管理器
    memory = MemoryStore()
    context_manager = ContextManager(memory)

    # 2. 模拟第一轮对话（添加长期记忆）
    memory.add_long_term_memory(
        scene="销售分析",
        result="2024年2月销售额100万，同比增长20%",
        export_path="./202402_sales_report.xlsx",
        time_range="2024年2月"
    )

    # 3. 模拟第二轮用户输入（未提及场景和时间）
    user_input = "帮我生成对应的Excel报表"
    context_manager.update_context(user_input)

    # 4. 验证上下文功能
    print("=== 完整格式化上下文 ===")
    print(context_manager.get_full_context())

    print("\n=== 提取的关键上下文 ===")
    print(context_manager.extract_key_context())

    print("\n=== 上下文完整性校验 ===")
    is_complete, missing_fields = context_manager.validate_context(required_fields=["scene", "time_range", "operation"])
    print(f"上下文是否完整：{is_complete}")
    print(f"缺失字段：{missing_fields}")