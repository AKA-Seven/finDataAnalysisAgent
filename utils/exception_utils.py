"""
异常工具：定义项目专属自定义异常，便于异常分类和排查
"""

class AgentBaseException(Exception):
    """Agent项目基础异常（所有自定义异常的父类）"""
    def __init__(self, message: str = ""):
        self.message = f"Agent异常：{message}"
        super().__init__(self.message)

class ConfigException(AgentBaseException):
    """配置相关异常（如配置文件不存在、配置项缺失）"""
    def __init__(self, message: str = ""):
        self.message = f"配置异常：{message}"
        super().__init__(self.message)

class TaskExecuteException(AgentBaseException):
    """任务执行相关异常（如MCP模块执行失败、任务分发失败）"""
    def __init__(self, message: str = ""):
        self.message = f"任务执行异常：{message}"
        super().__init__(self.message)

class DataProcessException(AgentBaseException):
    """数据处理相关异常（如数据格式错误、缺失核心字段）"""
    def __init__(self, message: str = ""):
        self.message = f"数据处理异常：{message}"
        super().__init__(self.message)

class FileOperateException(AgentBaseException):
    """文件操作相关异常（如文件读写失败、目录创建失败）"""
    def __init__(self, message: str = ""):
        self.message = f"文件操作异常：{message}"
        super().__init__(self.message)