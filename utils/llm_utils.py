
# utils/llm_utils.py
"""
LLM工具模块（DeepSeek API封装）
主要功能：
- 简单chat调用（返回纯文本）
- 支持系统提示、温度、max_tokens自定义
- 错误处理与重试（基础版）
后续扩展：支持tool calling、streaming、multi-turn历史管理
"""
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from typing import List, Dict, Optional
from config import config
import json

def call_deepseek(
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    system_prompt: Optional[str] = None,
) -> str:
    url = config.DEEPSEEK.BASE_URL.rstrip("/") + config.DEEPSEEK.ENDPOINT
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.DEEPSEEK.API_KEY}",
    }

    final_messages = messages.copy()
    if system_prompt:
        final_messages.insert(0, {"role": "system", "content": system_prompt})

    payload = {
        "model": config.DEEPSEEK.MODEL,
        "messages": final_messages,
        "temperature": temperature if temperature is not None else config.DEEPSEEK.temperature,
        "max_tokens": max_tokens if max_tokens is not None else config.DEEPSEEK.max_tokens,
        "stream": False,
    }

    try:
        # 添加重试机制：最多3次，重试服务器错误
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])  # 服务器错误重试
        session.mount('https://', HTTPAdapter(max_retries=retries))

        # 增加超时到60秒
        response = session.post(
            url,
            headers=headers,
            json=payload,
            timeout=60,  # 增加超时时间，避免快速卡死
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        raise RuntimeError("API 请求超时，请检查网络或稍后重试。")
    except requests.exceptions.HTTPError as e:
        error_detail = response.text
        raise RuntimeError(f"DeepSeek API 错误 {response.status_code}: {error_detail}") from e
    except (KeyError, json.JSONDecodeError) as e:
        raise RuntimeError(f"DeepSeek 响应解析错误: {response.text}") from e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"DeepSeek 请求失败: {str(e)}") from e