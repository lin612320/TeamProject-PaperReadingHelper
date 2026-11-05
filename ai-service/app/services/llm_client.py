"""调用 DeepSeek 的 OpenAI 兼容接口。"""

import json
import os
import socket
import urllib.error
import urllib.request
from dotenv import load_dotenv

load_dotenv()
DEFAULT_TIMEOUT = 20

class LLMTimeout(Exception):
    """大模型请求超时。"""

class LLMError(Exception):
    """大模型调用失败（未配置 Key、网络错误、返回格式异常等）。"""

def model_name():
    return os.getenv("LLM_MODEL", "deepseek-chat")

def _endpoint():
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    return base_url.rstrip("/") + "/chat/completions"

def chat(messages, timeout=DEFAULT_TIMEOUT):
    """发一次对话补全，返回 (answer, usage)。

    参数:
        messages: OpenAI 格式的消息列表
        timeout: 超时秒数
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if api_key == "":
        raise LLMError("未配置 DEEPSEEK_API_KEY")

    payload = {
        "model": model_name(),
        "messages": messages,
        "temperature": 0,
        "stream": False,
    }
    request = urllib.request.Request(
        _endpoint(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
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
