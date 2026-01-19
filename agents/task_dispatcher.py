# agents/task_dispatcher.py
"""
任务分发器：分类用户输入，分发到ReAct或直接LLM
修复：显式导入 List, Dict
"""

from typing import List, Dict  # 修复：显式导入
from utils.llm_utils import call_deepseek
from .react_agent import run_react_agent

class TaskDispatcher:
    def __init__(self, conv_manager: "ConversationManager"):
        self.conv_manager = conv_manager

    def dispatch(self, user_query: str) -> str:
        # Fallback 分类：如果包含关键词如"数据库"、"报告"、"代码"，视为 complex
        keywords_complex = ["数据库", "查询", "报告", "代码", "分析", "excel", "word"]
        if any(word in user_query.lower() for word in keywords_complex):
            classification = "complex"
        else:
            # 仅当不确定时调用 API 分类（减少调用次数）
            classify_prompt = [
                {"role": "system", "content": "分类查询：'simple'（无需工具，直接回答）或 'complex'（需工具如DB/代码/报告）。仅输出分类词。"},
                {"role": "user", "content": user_query}
            ]
            try:
                classification = call_deepseek(classify_prompt).strip().lower()
            except Exception as e:
                classification = "simple"  # 错误时 fallback 到 simple

        self.conv_manager.append_message("user", user_query)

        history = self.conv_manager.get_history()

        if classification == "simple":
            try:
                response = call_deepseek(history)
            except Exception as e:
                response = f"简单响应失败：{str(e)}"  # 防止卡死
            self.conv_manager.append_message("assistant", response)
            return response
        else:
            response, updated_history = run_react_agent(user_query, history=history)
            self.conv_manager.history = updated_history
            self.conv_manager.append_message("assistant", response)
            self.conv_manager.summarize_if_long()
            return response