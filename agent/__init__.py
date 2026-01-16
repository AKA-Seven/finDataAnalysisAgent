"""
Agent 核心模块
封装多轮对话、指令解析、任务调度能力，是项目的核心调度中枢
"""

# 导出子模块的核心类（通过__all__控制，避免直接暴露子模块）
from .core import BaseAgent, ReportAgent
from .dialogue import ContextManager, MemoryStore
from .parser import NLParser, TaskStructor, ScenarioMatcher
from .scheduler.task_dispatcher import TaskDispatcher
from .scheduler.result_assembler import ResultAssembler
from .agent_bootstrap import AIReportAgent  # 新增：导出全局 Agent 类

# 对外暴露的核心类
__all__ = [
    # Core
    "BaseAgent",
    "ReportAgent",
    # Dialogue
    "ContextManager",
    "MemoryStore",
    # Parser
    "NLParser",
    "TaskStructor",
    "ScenarioMatcher",
    # Scheduler
    "TaskDispatcher",
    "ResultAssembler",
    # Bootstrap（全局 Agent）
    "AIReportAgent"
]