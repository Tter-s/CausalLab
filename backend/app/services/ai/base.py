"""Provider 基类与统一异常。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class AIRequest:
    system: str
    user: str
    task_type: str = "general"
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(slots=True)
class AIResponse:
    text: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    mock: bool = False


class AIError(Exception):
    """AI 调用相关错误的基类。"""

    user_message = "AI 调用失败"


class AINotConfigured(AIError):
    user_message = "AI 未配置。请在「设置 → AI 服务」中配置云端 API，或使用无 AI 模式下的规则分析。"


class AIConfirmRequired(AIError):
    """隐私确认未通过：需要用户确认要发送的内容后重试。"""

    def __init__(self, payload_preview: str, provider: str, model_id: str):
        self.payload_preview = payload_preview
        self.provider = provider
        self.model_id = model_id
        super().__init__("用户尚未确认发送内容到云端模型")

    user_message = "发送内容需要用户确认"


class AIBudgetExceeded(AIError):
    user_message = "本月 AI 用量已超过预算上限。可在设置中调整预算或等待下月。"


class AIUpstreamError(AIError):
    user_message = "云端模型服务不可用或返回错误。"


class AIResponseInvalid(AIError):
    user_message = "模型输出不符合预期的结构化格式。"


class AIProvider(ABC):
    provider_id: str = "base"

    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResponse: ...
