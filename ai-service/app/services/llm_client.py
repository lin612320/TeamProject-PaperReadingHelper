"""调用 OpenAI 兼容接口（默认 DeepSeek）。"""

import json
import os
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()
DEFAULT_TIMEOUT = 20

class LLMTimeout(Exception):
    """大模型请求超时。"""

class LLMError(Exception):
    """大模型调用失败（未配置 Key、网络错误、返回格式异常等）。"""

def model_name(model=None):
    """本次请求使用的模型名：请求参数优先，其次 .env。"""
    if model is not None and model.strip() != "":
        return model.strip()
    return os.getenv("LLM_MODEL", "deepseek-chat")

def _base_url(base_url=None):
    url = (
        base_url
        if base_url is not None
        else os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    ).strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise LLMError("API 地址不合法，必须是以 http:// 或 https:// 开头的完整地址")
    return url

def _endpoint(base_url=None):
    return _base_url(base_url) + "/chat/completions"

def chat(messages, timeout=DEFAULT_TIMEOUT, api_key=None, base_url=None, model=None):
    """发一次对话补全，返回 (answer, usage)。

    参数:
        messages: OpenAI 格式的消息列表
        timeout: 超时秒数
        api_key: 可选，本次请求使用的 Key；不传则读 .env
        base_url: 可选，本次请求使用的接口地址；不传则读 .env
        model: 可选，本次请求使用的模型名；不传则读 .env
    """
    provided_key = api_key.strip() if api_key is not None else ""
    effective_base = base_url.strip() if base_url is not None and base_url.strip() != "" else None
    if effective_base is not None and provided_key == "":
        # 防止把服务端 .env 里的 Key 发往用户指定的任意地址
        raise LLMError("使用自定义 API 地址时必须同时提供 API Key")

    key = provided_key or os.getenv("DEEPSEEK_API_KEY", "").strip()
    if key == "":
        raise LLMError("未配置 DEEPSEEK_API_KEY")

    payload = {
        "model": model_name(model),
        "messages": messages,
        "temperature": 0,
        "stream": False,
    }
    request = urllib.request.Request(
        _endpoint(effective_base),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except (socket.timeout, TimeoutError):
        raise LLMTimeout("大模型请求超时")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        raise LLMError("大模型返回 HTTP %s: %s" % (e.code, detail))
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            raise LLMTimeout("大模型请求超时")
        raise LLMError("大模型连接失败: %s" % e.reason)

    try:
        data = json.loads(body)
        answer = data["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError("大模型返回格式异常: %s" % e)

    usage = data.get("usage")
    if usage is None:
        usage = {}
    return answer, usage
