# agent/parser/__init__.py
"""
业务指令解析模块（parser）
核心功能：自然语言指令解析→结构化Task生成→场景-宽表映射补全
对外暴露：NLParser（自然语言解析）、Task（结构化任务）、TaskStructor（任务转换）、ScenarioMatcher（场景匹配）
"""

# 统一绝对导入（兼容外部调用）
from agent.parser.nl_parser import NLParser
from agent.parser.task_structor import Task, TaskStructor
from agent.parser.scenario_matcher import ScenarioMatcher

# 定义对外暴露的类列表（限制外部导入范围，隐藏内部私有方法/类）
__all__ = ["NLParser", "Task", "TaskStructor", "ScenarioMatcher"]

# 模块版本信息
__version__ = "1.0.0"