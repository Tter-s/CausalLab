"""AI 结构化输出 Schema 与提示词构建。

约束：AI 输出只作为「分析建议」，永远通过 Pydantic 校验后由应用层写库；
所有提示词都要求区分事实/推测、给出不确定性说明、不得做绝对断言。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class AIDiagnosisOut(BaseModel):
    category: str = Field(
        description="诊断类别：concept_gap/retrieval_failure/method_selection/execution_error/transfer_failure/other/insufficient_data"
    )
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, description="诊断依据，必须引用给出的答题记录编号")
    evidence_attempt_ids: list[int] = []
    alternatives: list[AIDiagnosisAlternative] = Field(default_factory=list, min_length=1)


class AIDiagnosisAlternative(BaseModel):
    category: str
    likelihood: str  # high/medium/low/unknown
    reason: str = ""


class AISuggestionOut(BaseModel):
    suggestions: list[str] = Field(min_length=1)
    verification_tasks: list[str] = Field(min_length=1, description="可执行的后续验证任务")


class AITAReviewOut(BaseModel):
    summary: str
    facts: list[str] = []
    speculations: list[str] = []
    missing_evidence: list[str] = []
    improvements: list[str] = []


class AIDTMReviewOut(BaseModel):
    summary: str
    process_score: int = Field(ge=1, le=5)
    lessons: list[str] = []
    bias_flags: list[str] = []


class AICounterfactualOut(BaseModel):
    analysis: str
    caveats: list[str] = []


class AIHypothesisDesignOut(BaseModel):
    measurement_plan: str
    data_needed: list[str] = []
    caveats: list[str] = []
    suggested_duration_days: int = Field(default=14, ge=1, le=365)


class AILoopReviewOut(BaseModel):
    verdict: str = Field(description="effective/ineffective/uncertain 之一")
    reasoning: str
    next_strategy: list[str] = []


# ---------- 提示词 ----------

DIAGNOSIS_SYSTEM = (
    "你是学习诊断助手。根据用户在某个知识点上的答题记录，判断其学习障碍最可能属于哪一类。"
    "类别只能是：concept_gap(概念不理解)、retrieval_failure(知识提取失败)、method_selection(方法选择困难)、"
    "execution_error(推理执行困难)、transfer_failure(知识迁移困难)、other。"
    "硬性规则：1) 如果样本太少（少于3条记录或失败少于2次），必须输出 category=insufficient_data 且 confidence<=0.25；"
    "2) 不得断言，只能给出概率性判断；3) rationale 必须引用具体记录编号；"
    "4) 必须给出至少一个备选解释(alternatives)；5) 用中文。"
)

SUGGESTION_SYSTEM = (
    "你是学习建议助手。针对给定的诊断结果，给出可执行的学习建议与后续验证任务。"
    "建议必须具体可操作，不要泛泛而谈；验证任务必须能在 48 小时~1 周内独立完成并明确判定成败。用中文。"
)

TA_REVIEW_SYSTEM = (
    "你是项目复盘助手。根据项目的过程数据（任务耗时、阻塞、返工、中断、需求变化），输出复盘报告。"
    "硬性规则：1) 事实(facts)只能陈述数据直接支持的结论；2) 推测(speculations)必须以“推测”开头并说明依据；"
    "3) 必须指出缺失证据(missing_evidence)；4) 改进建议(improvements)必须可在下个项目验证；"
    "5) 不得用结果好坏简单评判决策或能力。用中文。"
)

DTM_REVIEW_SYSTEM = (
    "你是决策复盘助手。根据决策记录、当时预测与实际结果，评估这次决策的过程质量。"
    "硬性规则：1) 结果好不代表决策正确，结果差也不代表决策错误（结果偏见）；"
    "2) process_score 评估的是决策过程（信息收集、备选方案、概率校准），1~5 分；"
    "3) lessons 给出可迁移的经验，bias_flags 指出可能的认知偏差。用中文。"
)

COUNTERFACTUAL_SYSTEM = (
    "你是反事实推演助手。基于决策记录推演“如果当初选择另一个方案会怎样”。"
    "硬性规则：1) 这是假设推演不是事实，输出中必须明确说明这一点；"
    "2) 推演必须基于已记录的依据，注明哪些是推测；3) 不得用推演结果评判当初决策的对错。用中文。"
)

HYP_DESIGN_SYSTEM = (
    "你是自我实验设计助手。帮用户把关于自身学习/工作方式的假设变成可执行的小型记录实验。"
    "要求：测量计划必须具体（记录什么、何时记录、如何分组）；必须说明局限性（相关≠因果、样本小、无法控制变量）。用中文。"
)

LOOP_REVIEW_SYSTEM = (
    "你是改进循环复盘助手。根据循环的干预措施与收集到的数据，判断干预是否有效。"
    "硬性规则：1) verdict 只能是 effective/ineffective/uncertain；证据不足时必须选 uncertain；"
    "2) reasoning 必须引用数据；3) next_strategy 给出下一步可测试的具体调整。用中文。"
)
