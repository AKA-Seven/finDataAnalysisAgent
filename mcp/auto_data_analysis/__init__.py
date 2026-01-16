# -*- coding: utf-8 -*-
"""
自动化数据分析模块（auto_data_analysis）
核心功能：输入宽表DataFrame+自然语言需求，生成Python自动化分析代码
特性：1. 支持任意自定义分析功能，不限定统计/趋势/异常三类；2. 无具体需求时回退到标准分析流程
适配场景：金融结算、运营销售、成本管控等各类宽表数据的自动化分析与结果汇总
"""

# 导入核心入口类，简化外部导入（隐藏内部实现）
from .descriptive_analysis import DescriptiveAnalysis

# 定义公共API（仅暴露核心入口类，外部无需关注内部细节）
__all__ = [
    "DescriptiveAnalysis"
]

# 模块版本信息
__version__ = "1.0.0"

# 默认大模型配置（贴合DeepSeek，作兜底使用，外部可覆盖）
DEFAULT_LLM_CONFIG = {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model_name": "deepseek-chat",
    "endpoint": "/v1/chat/completions",
    "max_tokens": 3000,
    "temperature": 0.1
}