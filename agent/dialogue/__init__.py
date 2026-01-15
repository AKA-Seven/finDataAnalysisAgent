# agent/dialogue/__init__.py
"""
对话管理模块（dialogue）
核心功能：维护对话记忆（短期/长期）、整合对话上下文、提取关键信息
对外暴露：MemoryStore（记忆存储）、ContextManager（上下文管理）
"""

# 从当前模块导入核心类
from .memory_store import MemoryStore
from .context_manager import ContextManager

# 定义对外暴露的类列表（限制外部导入范围，隐藏内部私有方法/类）
__all__ = ["MemoryStore", "ContextManager"]

# 模块版本信息
__version__ = "1.0.0"