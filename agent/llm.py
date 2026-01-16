"""LLM模块：调用DeepSeek API"""
import requests
from config import get_llm_config
from utils import get_logger, TaskExecuteException

# 获取日志实例
logger = get_logger(__name__)

# 加载DeepSeek配置（从config/llm_config.yaml读取）
LLM_CONFIG = get_llm_config()["deepseek"]

class DeepSeekLLM:
    """DeepSeek LLM API封装"""
    def __init__(self):
        self.api_key = LLM_CONFIG["API_KEY"]
        self.base_url = LLM_CONFIG["BASE_URL"]
        self.model = LLM_CONFIG["MODEL"]
        self.endpoint = LLM_CONFIG["ENDPOINT"]
        self.full_url = f"{self.base_url}{self.endpoint}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.timeout = LLM_CONFIG.get("timeout", 30)

    def chat_completion(self, messages: list) -> str:
        """
        调用DeepSeek聊天完成接口
        :param messages: 对话消息列表（格式：[{"role": "user", "content": "查询2024年2月成本数据"}]）
        :return: LLM返回结果
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": LLM_CONFIG.get("max_tokens", 2048),
                "temperature": LLM_CONFIG.get("temperature", 0.7)
            }

            response = requests.post(
                url=self.full_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()  # 抛出HTTP请求异常

            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"DeepSeek LLM API调用失败：{str(e)}")
            raise TaskExecuteException(f"LLM API调用失败：{str(e)}")