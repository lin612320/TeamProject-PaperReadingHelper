"""划词翻译/术语解释逻辑脚本。
边界：利用论文标题和上下文辅助理解，但只翻译或解释用户选中的那段文本。
"""

import re
from app.services import llm_client
from app.services.llm_config import LlmConfig

MAX_TEXT = 1000          # 选中文本截断
MAX_CONTEXT = 600        # 上下文辅助的最大篇幅
TIMEOUT_SECONDS = 10     # 单次模型调用时限
VALID_MODES = ("translate", "term")

class ExplainError(Exception):
    """划词解释链路异常。
    契约:code 使用内部错误码，路由层据此返回 HTTP 状态码。
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message

def _build_messages(title, context, text, mode):
    """构造prompt"""
    context_block = ""
    if context:
        context_block = (
            "相关上下文（节选，仅用于理解术语，不要翻译或解释它）：\n%s\n\n" % context
        )

    if mode == "translate":
        system = (
            "你是严谨的论文阅读助手，负责把论文中选中的英文翻译成中文。"
            "只翻译用户给出的「选中文本」，不要翻译上下文，也不要补充原文之外的信息。"
            "严格按以下两行输出，不要加其他内容：\n"
            "翻译：<中文译文>\n"
            "解释：<可为空；若有必要，用一句中文说明>"
        )
        action = "请翻译选中文本。"
    else:
        system = (
            "你是严谨的论文阅读助手，负责解释论文中的专业术语。"
            "只解释用户给出的「选中文本」，不要解释上下文，也不要编造。"
            "解释的第一句必须是通俗易懂的白话定义；第二句起再补充专业细节，"
            "以及在本文语境中的含义。"
            "严格按以下两行输出，不要加其他内容：\n"
            "翻译：<中文术语>\n"
            "解释：<第一句白话定义，然后补充>"
        )
        action = "请解释选中文本。"

    user = "论文标题：%s\n%s选中文本：\n%s\n%s" % (
        title or "（未提供）",
        context_block,
        text,
        action,
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

def _parse_answer(answer):
    """解析模型返回的文本。"""
    text = answer.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()

    translation = ""
    explanation = ""

    match = re.search(r"翻译\s*[：:]\s*(.*?)(?=\n\s*解释\s*[：:]|\Z)", text, re.S)
    if match:
        translation = match.group(1).strip()

    match = re.search(r"解释\s*[：:]\s*(.*)\Z", text, re.S)
    if match:
        explanation = match.group(1).strip()

    # 格式完全不合规时，保留文本
    if translation == "" and explanation == "":
        explanation = text

    return translation, explanation

def explain_text(title, context, text, mode, config=None):
    """翻译或解释一段选中文本。

    参数:
        title: 论文标题（未入库论文默认为空）
        context: 上下文
        text: 选中的文本
        mode: translate/term
        config: LlmConfig，未传则用服务端 .env

    返回:
        {translation, explanation, mode, truncated}
    """
    if mode not in VALID_MODES:
        raise ExplainError("INVALID_MODE", "mode 只能是 translate 或 term")

    text = text.strip()
    if text == "":
        raise ExplainError("EMPTY_TEXT", "选中文本不能为空")

    truncated = len(text) > MAX_TEXT
    if truncated:
        text = text[:MAX_TEXT]

    context = (context or "").strip()[:MAX_CONTEXT]
    messages = _build_messages(title, context, text, mode)

    if config is None:
        config = LlmConfig()

    try:
        answer, _usage = llm_client.chat_with_config(
            messages, config, timeout=TIMEOUT_SECONDS
        )
    except llm_client.LLMTimeout:
        raise ExplainError("LLM_TIMEOUT", "大模型请求超时")
    except llm_client.LLMAuthError as e:
        raise ExplainError("LLM_AUTH_ERROR", "大模型鉴权失败: " + str(e))
    except Exception as e:
        raise ExplainError("LLM_ERROR", "大模型调用失败: " + str(e))

    translation, explanation = _parse_answer(answer)
    return {"translation": translation,"explanation": explanation,"mode": mode,"truncated": truncated}
