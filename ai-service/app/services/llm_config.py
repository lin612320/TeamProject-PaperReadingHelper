"""大模型调用配置
模块独立：方面后续功能扩展（如让用户可以自定义不同服务所使用的大语言模型API）
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class LlmConfig:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None

    @classmethod
    def from_request(cls, api_key=None, base_url=None, model=None):
        return cls(api_key=api_key, base_url=base_url, model=model)
