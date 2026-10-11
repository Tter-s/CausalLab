"""AI Provider 抽象层。

设计约束（见任务书第三节）：
- 只支持云端 OpenAI 兼容 API，不做本地模型部署；
- 「完全无 AI」是默认模式且是一等公民（provider="none"）；
- MockProvider 供自动化测试与无 Key 演示，测试中绝不调用真实 API；
- 所有调用经服务端代理，API Key 不进前端/日志/错误报告。
"""
from __future__ import annotations

from app.services.ai.base import (
    AIBudgetExceeded,
    AIError,
    AINotConfigured,
    AIRequest,
    AIResponse,
    AIResponseInvalid,
    AIUpstreamError,
)
from app.services.ai.config import (
    AIConfirmRequired,
    estimate_cost,
    get_ai_config,
    get_provider,
    mask_config,
    month_cost_so_far,
    run_structured,
    save_ai_config,
)
from app.services.ai.mock import MockProvider
from app.services.ai.openai_compat import OpenAICompatProvider

__all__ = [
    "AIError",
    "AIRequest",
    "AIResponse",
    "AIBudgetExceeded",
    "AINotConfigured",
    "AIResponseInvalid",
    "AIUpstreamError",
    "AIConfirmRequired",
    "OpenAICompatProvider",
    "MockProvider",
    "get_ai_config",
    "get_provider",
    "save_ai_config",
    "mask_config",
    "run_structured",
    "estimate_cost",
    "month_cost_so_far",
]
