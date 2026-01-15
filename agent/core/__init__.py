# agent/core/__init__.py
"""
Agent核心逻辑模块（core）
核心功能：封装Agent通用流程（对话初始化、指令解析、记忆管理）、实现金融报表专属业务逻辑
对外暴露：BaseAgent（抽象基类）、ReportAgent（金融报表专属Agent）
"""

# 统一绝对导入：核心Agent类
from agent.core.base_agent import BaseAgent
from agent.core.report_agent import ReportAgent

# 定义对外暴露的类列表（限制外部导入范围，隐藏内部私有方法/类）
__all__ = ["BaseAgent", "ReportAgent"]

# 模块版本信息
__version__ = "1.0.0"