"""OpenAI 兼容云端 Provider（覆盖 DeepSeek / MiMo / Moonshot / 其他兼容服务）。

- 本机网络实测：api.deepseek.com、api.moonshot.cn 可达；api.openai.com 不可达（适配代码保留，标注“本机未验证”）。
- 所有请求经服务端发出，API Key 仅存在于服务端进程内存与加密存储中。
"""
from __future__ import annotations

import asyncio
import json
import time

import httpx

from app.services.ai.base import AIProvider, AIRequest, AIResponse, AIUpstreamError

_RETRY_STATUS = {429, 500, 502, 503, 504}


def _estimate_tokens(text: str) -> int:
    # 中文约 1 token/字，英文约 4 字符/token，取中间估计
    return max(1, len(text) // 2)


class OpenAICompatProvider(AIProvider):
    provider_id = "openai-compat"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        temperature: float | None = 0.4,
        max_tokens: int = 2048,
        label: str = "openai-compat",
    ) -> None:
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider_id = label  # deepseek / mimo / moonshot / openai-compat 仅用于展示

    def endpoint(self) -> str:
        b = self.base_url
        if b.endswith("/chat/completions"):
            return b
        if b.endswith("/v1"):
            return f"{b}/chat/completions"
        return f"{b}/v1/chat/completions"

    async def complete(self, request: AIRequest) -> AIResponse:
        if not self.api_key:
            raise AIUpstreamError("API Key 为空")
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "stream": False,
            "max_tokens": request.max_tokens or self.max_tokens,
        }
        temperature = request.temperature if request.temperature is not None else self.temperature
        if temperature is not None:
            payload["temperature"] = temperature

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = self.endpoint()
        last_error = ""

        for attempt in range(3):
            start = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                latency_ms = int((time.monotonic() - start) * 1000)
                if resp.status_code == 200:
                    data = resp.json()
                    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
                    usage = data.get("usage") or {}
                    pt = int(usage.get("prompt_tokens") or _estimate_tokens(request.system + request.user))
                    ct = int(usage.get("completion_tokens") or _estimate_tokens(content))
                    return AIResponse(
                        text=content,
                        provider=self.provider_id,
                        model=self.model,
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        latency_ms=latency_ms,
                    )
                # 记录错误时不包含 headers，避免泄露 Key
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                if resp.status_code in _RETRY_STATUS and attempt < 2:
                    await asyncio.sleep(0.6 * (2**attempt))
                    continue
                raise AIUpstreamError(last_error)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = f"网络错误: {type(exc).__name__}"
                if attempt < 2:
                    await asyncio.sleep(0.6 * (2**attempt))
                    continue
                raise AIUpstreamError(last_error) from exc
        raise AIUpstreamError(last_error or "未知错误")

    @staticmethod
    def extract_json(text: str) -> str:
        """剥离模型输出中常见的 ```json 围栏，返回纯 JSON 字符串。"""
        t = text.strip()
        if t.startswith("```"):
            t = t.strip("`")
            if t.lower().startswith("json"):
                t = t[4:]
        start = t.find("{")
        end = t.rfind("}")
        if start >= 0 and end > start:
            t = t[start : end + 1]
        return t

    @staticmethod
    def parse_json_obj(text: str) -> dict:
        raw = OpenAICompatProvider.extract_json(text)
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AIUpstreamError(f"输出不是合法 JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise AIUpstreamError("输出不是 JSON 对象")
        return obj
