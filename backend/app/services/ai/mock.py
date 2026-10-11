"""MockProvider：确定性、结构正确的模拟输出。

用途：
1. 自动化测试（绝不调用真实 API）；
2. 用户没有 API Key 时预览「AI 分析」的交互流程（界面明确标注“模拟输出”）。
"""
from __future__ import annotations

from app.services.ai.base import AIProvider, AIRequest, AIResponse


def _canned(request: AIRequest) -> str:
    tt = request.task_type
    if tt == "kd_diagnosis":
        return (
            '{"category": "concept_gap", "confidence": 0.55,'
            ' "rationale": "【模拟输出】多次答题在同类型步骤上卡住，且在不涉及该概念的新题上表现正常，'
            "提示可能是概念本身未建立，而非粗心。该判断需要更多独立完成的样本支持。\","
            ' "evidence_attempt_ids": [],'
            ' "alternatives": [{"category": "retrieval_failure", "likelihood": "medium",'
            ' "reason": "【模拟】若提示后能顺利做出来，更可能是提取失败。"},'
            '{"category": "method_selection", "likelihood": "low", "reason": "【模拟】暂无方法选择混乱的证据。"}]}'
        )
    if tt == "kd_suggestion":
        return (
            '{"suggestions": ["【模拟输出】用费曼技巧向自己复述该概念的定义，并写下卡壳点。",'
            ' "【模拟】找 3 道只有单一考点的基础题，限时独立完成。",'
            ' "【模拟】把错题步骤拆成流程图，标出第一次偏离的位置。"],'
            ' "verification_tasks": ["【模拟验证题】独立完成一道该概念的基础题，不看任何资料。",'
            ' "【模拟验证题】48 小时后重做本次错题，记录是否需要提示。"]}'
        )
    if tt == "ta_review":
        return (
            '{"summary": "【模拟输出】项目整体延期，阻塞集中在个别任务上；以下内容仅基于已记录的过程数据，'
            '其中推测部分需要更多证据。",'
            ' "facts": ["【模拟·事实】有任务发生了阻塞且记录了阻塞时长。",'
            ' "【模拟·事实】实际耗时与预估存在偏差的任务超过一个。"],'
            ' "speculations": ["【模拟·推测】阻塞可能与外部依赖等待有关，但缺少等待原因的记录。"],'
            ' "missing_evidence": ["【模拟·缺失】中断发生的具体上下文没有记录，无法判断是内因还是外因。"],'
            ' "improvements": ["【模拟】下一次预估时给关键任务乘以 1.5 的偏差系数，并用一个任务验证。",'
            ' "【模拟】阻塞发生时立即记录原因分类，积累两周期后再分析。"]}'
        )
    if tt == "dtm_review":
        return (
            '{"summary": "【模拟输出】该决策的复盘仅基于记录信息，重点是决策过程质量而非结果好坏。",'
            ' "process_score": 3,'
            ' "lessons": ["【模拟】备选方案当时只列了两个，可能遗漏了第三选项。",'
            ' "【模拟】预测概率缺少依据说明，复盘时难以校准。"],'
            ' "bias_flags": ["【模拟】注意结果偏见：结果好不代表决策过程对。"]}'
        )
    if tt == "dtm_counterfactual":
        return (
            '{"analysis": "【模拟输出·假设推演】如果当时选择另一方案，基于已记录的依据推断可能的结果是……'
            '这是假设推演，不是事实，也不能证明当初的决策错误。",'
            ' "risks_of_this_reasoning": ["假设情景无法还原真实环境的不确定性。"]}'
        )
    if tt == "hyp_design":
        return (
            '{"measurement_plan": "【模拟输出】每天按固定标准记录一次观察值，持续两周；'
            '记录时同时写下可能的干扰因素。",'
            ' "data_needed": ["每天至少 1 条观察", "记录当时的情境标签（如时段）"],'
            ' "caveats": ["个人观察不是随机对照实验，只能发现相关，不能证明因果。",'
            ' "样本量小时波动大，不要过早下结论。"],'
            ' "suggested_duration_days": 14}'
        )
    if tt == "loop_review":
        return (
            '{"verdict": "uncertain",'
            ' "reasoning": "【模拟输出】当前证据不足以判断干预是否有效，需要再收集一个周期的数据。",'
            ' "next_strategy": ["【模拟】延长观察周期至两周。", "【模拟】固定测量时间，减少记录误差。"]}'
        )
    return '{"summary": "【模拟输出】这是 MockProvider 的通用回复，用于无 Key 演示。"}'


class MockProvider(AIProvider):
    provider_id = "mock"

    async def complete(self, request: AIRequest) -> AIResponse:
        text = _canned(request)
        return AIResponse(
            text=text,
            provider=self.provider_id,
            model="mock-1",
            prompt_tokens=len(request.system + request.user) // 2,
            completion_tokens=len(text) // 2,
            latency_ms=1,
            mock=True,
        )
