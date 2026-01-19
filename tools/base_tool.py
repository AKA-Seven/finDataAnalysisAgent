# tools/base_tool.py
"""
工具基类（可选文件，如果放在tools目录下）
所有工具继承此基类，提供统一接口，便于Agent注册和调用
"""

from abc import ABC, abstractmethod

class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, input_str: str) -> str:
        """
        执行工具
        input_str: 字符串（通常为JSON格式）
        返回: Observation字符串（纯文本，包含结果描述 + 文件路径）
        """
        pass