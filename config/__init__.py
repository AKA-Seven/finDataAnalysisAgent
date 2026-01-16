"""
配置模块：统一加载/管理项目所有YAML配置，提供单例缓存避免重复读取
兼容agent/core、mcp各子模块的配置需求
"""
import os
import yaml
from typing import Dict, Any

# 配置文件路径（自动关联当前目录下的YAML文件，无需手动修改路径）
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
GLOBAL_CONFIG_PATH = os.path.join(_CONFIG_DIR, "global_config.yaml")
NL2SQL_CONFIG_PATH = os.path.join(_CONFIG_DIR, "nl2sql_config.yaml")
OFFICE_CONFIG_PATH = os.path.join(_CONFIG_DIR, "office_config.yaml")
SCENARIO_WIDETABLE_MAPPING_PATH = os.path.join(_CONFIG_DIR, "scenario_widetable_mapping.yaml")
LLM_CONFIG_PATH = os.path.join(_CONFIG_DIR, "llm_config.yaml")  # 新增：LLM配置路径

# 全局配置缓存（单例模式，避免重复加载YAML文件）
_global_config: Dict[str, Any] = {}
_nl2sql_config: Dict[str, Any] = {}
_office_config: Dict[str, Any] = {}
_scenario_mapping: Dict[str, Any] = {}
_llm_config: Dict[str, Any] = {}  # 新增：LLM配置缓存

def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """
    通用YAML配置加载函数（兼容中文，处理文件不存在异常）
    :param file_path: YAML配置文件路径
    :return: 配置字典
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"配置文件不存在，请检查路径：{file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise Exception(f"加载YAML配置失败（{file_path}）：{str(e)}") from e

def get_global_config() -> Dict[str, Any]:
    """获取全局配置（单例缓存，仅首次加载）"""
    global _global_config
    if not _global_config:
        _global_config = load_yaml_config(GLOBAL_CONFIG_PATH)
    return _global_config

def get_nl2sql_config() -> Dict[str, Any]:
    """获取NL2SQL配置（单例缓存）"""
    global _nl2sql_config
    if not _nl2sql_config:
        _nl2sql_config = load_yaml_config(NL2SQL_CONFIG_PATH)
    return _nl2sql_config

def get_office_config() -> Dict[str, Any]:
    """获取Office解析配置（单例缓存）"""
    global _office_config
    if not _office_config:
        _office_config = load_yaml_config(OFFICE_CONFIG_PATH)
    return _office_config

def get_scenario_widetable_mapping() -> Dict[str, Any]:
    """获取场景-宽表映射配置（单例缓存，兼容ScenarioMatcher）"""
    global _scenario_mapping
    if not _scenario_mapping:
        _scenario_mapping = load_yaml_config(SCENARIO_WIDETABLE_MAPPING_PATH)
    return _scenario_mapping

def get_llm_config() -> Dict[str, Any]:  # 新增：获取LLM配置（单例缓存）
    """获取LLM API配置（单例缓存，兼容agent/llm.py）"""
    global _llm_config
    if not _llm_config:
        _llm_config = load_yaml_config(LLM_CONFIG_PATH)
    return _llm_config

# 对外暴露核心函数/常量（兼容现有模块导入，新增LLM相关）
__all__ = [
    "GLOBAL_CONFIG_PATH",
    "NL2SQL_CONFIG_PATH",
    "OFFICE_CONFIG_PATH",
    "SCENARIO_WIDETABLE_MAPPING_PATH",
    "LLM_CONFIG_PATH",  # 新增
    "load_yaml_config",
    "get_global_config",
    "get_nl2sql_config",
    "get_office_config",
    "get_scenario_widetable_mapping",
    "get_llm_config"  # 新增
]