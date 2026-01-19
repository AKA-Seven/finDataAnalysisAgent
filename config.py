# config.py
"""
全局配置文件
所有其他模块通过 `from config import config` 导入使用
包含：
- 数据库配置（MySQL）
- DeepSeek LLM 配置
- 其他全局配置（输出目录、ReAct循环限制、日志等，便于后续扩展）
"""

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).parent.resolve()


OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

@dataclass(frozen=True)
class DatabaseConfig:
    type: str = "mysql"
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "David7668"
    db_name: str = "financial_report_db"
    charset: str = "utf8mb4"
    pool_size: int = 10
    timeout: int = 30

@dataclass(frozen=True)
class DeepSeekConfig:
    API_KEY: str = "sk-fe09e253e6f14adba6cf56eb1e1c106c"
    BASE_URL: str = "https://api.deepseek.com"
    MODEL: str = "deepseek-chat"
    ENDPOINT: str = "/v1/chat/completions"
    timeout: int = 30
    max_tokens: int = 2048
    temperature: float = 0.7

@dataclass(frozen=True)
class AgentConfig:
    """ReAct Agent 相关全局配置"""
    max_iterations: int = 15
    thought_prefix: str = "Thought:"
    action_prefix: str = "Action:"
    observation_prefix: str = "Observation:"
    final_answer_prefix: str = "Final Answer:"

class Config:
    DATABASE = DatabaseConfig()
    DEEPSEEK = DeepSeekConfig()
    AGENT = AgentConfig()
    OUTPUT_DIR = OUTPUT_DIR
    ROOT_DIR = ROOT_DIR

config = Config()