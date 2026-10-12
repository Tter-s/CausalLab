"""共享枚举常量与自定义序列化类型。"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import WrapSerializer

# ---- 模块标识 ----
Module = Literal["kd", "ml", "dtm", "ta", "hyp", "loop", "sys"]

# ---- KD ----
KDErrorCategory = Literal[
    "concept_gap",  # 概念不理解
    "retrieval_failure",  # 知识提取失败
    "method_selection",  # 方法选择困难
    "execution_error",  # 推理执行困难
    "transfer_failure",  # 知识迁移困难
    "other",
    "none",
]
KDDiagCategory = Literal[
    "concept_gap",
    "retrieval_failure",
    "method_selection",
    "execution_error",
    "transfer_failure",
    "other",
    "insufficient_data",
]
KDDiagStatus = Literal["provisional", "user_confirmed", "rejected"]
KDSource = Literal["rule", "ai", "user"]

# ---- ML ----
MLRating = Literal[1, 2, 3, 4]
MLMetric = Literal["retention", "recall_speed", "delayed_test"]
MLExperimentStatus = Literal["setup", "running", "completed"]

# ---- DTM ----
DTMStatus = Literal["open", "reviewed", "archived"]
Significance = Literal["minor", "major"]

# ---- TA ----
TAProjectStatus = Literal["active", "done", "archived"]
TATaskStatus = Literal["todo", "doing", "blocked", "done", "cancelled"]
TATaskEventType = Literal[
    "blocked",
    "resumed",
    "rework",
    "interrupted",
    "requirement_change",
    "note",
    "status_change",
    "dependency_cleared",
]
ImprovementStatus = Literal["proposed", "trying", "adopted", "discarded"]

# ---- 跨模块 ----
EvidenceKind = Literal[
    "fact",
    "speculation",
    "missing_evidence",
    "ai_analysis",
    "user_correction",
    "user_input",
]
LinkRelation = Literal["spawned_from", "associated_with", "validates", "feedback_to"]
HypStatus = Literal["draft", "testing", "supported", "rejected", "uncertain"]
LoopStageName = Literal["observe", "hypothesize", "intervene", "measure", "review", "adjust"]
LoopVerdict = Literal["effective", "ineffective", "uncertain"]

# ---- 附件 ----
AttachmentKind = Literal["question", "solution", "other"]

# ---- AI ----
AITaskType = Literal[
    "kd_diagnosis",
    "kd_suggestion",
    "ta_review",
    "dtm_review",
    "dtm_counterfactual",
    "hyp_design",
    "loop_review",
    "general",
]
AIProviderKind = Literal["none", "deepseek", "mimo", "moonshot", "openai-compat", "mock"]


def _serialize_utc(value: datetime | None, handler, info) -> str | None:  # noqa: ANN001
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
    return value.isoformat()


UTCDateTime = Annotated[datetime | None, WrapSerializer(_serialize_utc)]
