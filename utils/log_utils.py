"""
日志工具：统一日志格式、输出路径、级别配置，支持控制台+文件双输出
"""
import logging
import os
from datetime import datetime
from .file_utils import ensure_dir
from config import get_global_config

# 全局日志配置
_LOG_CONFIG = None
_LOGGER_CACHE = {}

def init_logger(level: int = logging.INFO) -> None:
    """
    初始化全局日志配置（仅需执行一次）
    :param level: 日志级别（默认INFO）
    """
    global _LOG_CONFIG
    _LOG_CONFIG = get_global_config()

    # 1. 获取日志目录并创建
    log_dir = _LOG_CONFIG["path"]["log_dir"]
    ensure_dir(log_dir)

    # 2. 构造日志文件名
    log_filename = f"ai_report_agent_{datetime.now().strftime('%Y%m%d')}.log"
    log_file_path = os.path.join(log_dir, log_filename)

    # 3. 定义日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 4. 配置日志处理器（控制台+文件）
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(),  # 控制台输出
            logging.FileHandler(log_file_path, encoding="utf-8")  # 文件输出
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """
    获取日志实例（缓存实例，避免重复创建）
    :param name: 日志名称（通常为模块名/类名）
    :return: 日志实例
    """
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    # 若未初始化，先执行默认初始化
    if not _LOG_CONFIG:
        init_logger()

    logger = logging.getLogger(name)
    _LOGGER_CACHE[name] = logger
    return logger