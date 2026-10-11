"""KD 规则诊断引擎（无 AI 时的默认诊断路径）。

硬约束（任务书模块 A）：不得仅根据一道题或一次失败断言用户存在某种能力缺陷。
- 样本不足（总答题 < 3 或失败 < 2）时输出 insufficient_data 且置信度封顶 0.25；
- 置信度随样本量与错误类别一致性增长，封顶 0.85；
- 永远给出至少一个备选解释。
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORY_LABELS = {
    "concept_gap": "概念不理解",
    "retrieval_failure": "知识提取失败",
    "method_selection": "方法选择困难",
    "execution_error": "推理执行困难",
    "transfer_failure": "知识迁移困难",
    "other": "其他",
    "insufficient_data": "样本不足，暂不下结论",
}


@dataclass(slots=True)
class AttemptFact:
    id: int
    correct: bool
    error_category: str
    independent: bool
    notes: str = ""


def _consistency(votes: dict[str, int], total: int) -> float:
    if total == 0:
        return 0.0
    top = max(votes.values())
    return top / total


def rule_diagnose(attempts: list[AttemptFact]) -> dict:
    """基于答题事实的保守诊断。总是返回 dict（可能是 insufficient_data）。"""
    n = len(attempts)
    fails = [a for a in attempts if not a.correct]
    n_fails = len(fails)

    if n < 3 or n_fails < 2:
        return {
            "category": "insufficient_data",
            "confidence": 0.25 if n >= 1 else 0.0,
            "rationale": (
                f"当前共有 {n} 条答题记录（其中失败 {n_fails} 次）。样本不足以支持任何能力缺陷判断——"
                "一道题的失败可能只是状态波动或题目本身有歧义。请再完成几道同类题（最好独立完成），"
                "系统会基于更多样本给出更可靠的诊断。"
            ),
            "evidence_attempt_ids": [a.id for a in attempts],
            "alternatives": [
                {"category": "concept_gap", "likelihood": "unknown", "reason": "样本不足，无法比较各解释。"}
            ],
            "basis_attempt_count": n,
            "source": "rule",
        }

    # 统计失败记录中的错误类别票数
    votes: dict[str, int] = {}
    for a in fails:
        cat = a.error_category if a.error_category not in ("none", "") else "other"
        votes[cat] = votes.get(cat, 0) + 1

    top_cat = max(votes, key=votes.get)  # type: ignore[arg-type]
    consistency = _consistency(votes, n_fails)

    # “会做但不独立”的样本多 → 倾向迁移困难
    helped_correct = [a for a in attempts if a.correct and not a.independent]
    transfer_signal = len(helped_correct) >= 2 and top_cat in ("method_selection", "retrieval_failure")

    confidence = min(0.85, 0.3 + 0.1 * n_fails + 0.3 * consistency)
    if transfer_signal:
        confidence = min(0.8, confidence)

    rationale_parts = [
        f"基于 {n} 条答题记录（失败 {n_fails} 次）的统计：",
        f"失败记录中最多的错误类别是「{CATEGORY_LABELS.get(top_cat, top_cat)}」"
        f"（{votes[top_cat]}/{n_fails}），一致性 {consistency:.0%}。",
    ]
    if transfer_signal:
        rationale_parts.append(
            f"另有 {len(helped_correct)} 次在他人辅助下做对，独立完成时失败，提示知识迁移可能存在障碍。"
        )
    rationale_parts.append("这是统计推断而非确诊，请结合诊断依据判断是否符合你的实际体验。")

    # 备选解释：票数次高的类别 + 受辅助正确所暗示的迁移困难
    alternatives = []
    for cat, cnt in sorted(votes.items(), key=lambda kv: -kv[1]):
        if cat == top_cat:
            continue
        alternatives.append(
            {
                "category": cat,
                "likelihood": "medium" if cnt >= 2 else "low",
                "reason": f"失败记录中出现 {cnt} 次。",
            }
        )
    if transfer_signal and top_cat != "transfer_failure":
        alternatives.append(
            {
                "category": "transfer_failure",
                "likelihood": "medium",
                "reason": f"{len(helped_correct)} 次辅助下正确、独立时失败的模式支持该解释。",
            }
        )
    if not alternatives:
        alternatives.append(
            {"category": "other", "likelihood": "low", "reason": "当前证据不足以区分其他解释。"}
        )

    return {
        "category": top_cat,
        "confidence": round(confidence, 2),
        "rationale": " ".join(rationale_parts),
        "evidence_attempt_ids": [a.id for a in fails],
        "alternatives": alternatives[:3],
        "basis_attempt_count": n,
        "source": "rule",
    }


def rule_suggestions(category: str) -> dict:
    """针对诊断类别的通用学习建议与验证任务（无 AI 时的默认路径）。"""
    content_map = {
        "concept_gap": [
            "用自己的话写出该知识点的定义，再与教材/资料对照，标出差异。",
            "找 2 道只考察这个概念的题目，写出每一步的依据。",
        ],
        "retrieval_failure": [
            "先做主动回忆（合上资料复述要点），再看答案，而不是直接重读。",
            "把关键结论做成问答卡，进入记忆实验室按间隔复习。",
        ],
        "method_selection": [
            "列出你掌握的所有解题方法及各自适用条件，做题前先判断类型再选方法。",
            "复盘最近错题：当时有哪些线索提示应该用别的方法？",
        ],
        "execution_error": [
            "把解题过程拆成小步骤逐步验算，定位第一次出错的步骤。",
            "错题重做时放慢速度，写完整中间步骤，避免跳步。",
        ],
        "transfer_failure": [
            "收集 2~3 道情境不同但考点相同的题目，对比它们的共同结构。",
            "尝试向别人（或纸面）讲解该知识在陌生情境中如何应用。",
        ],
    }
    suggestions = content_map.get(
        category,
        ["再收集几条答题记录，区分错误是概念、方法还是执行层面的问题。"],
    )
    verification = [
        "验证任务：48 小时后独立完成 1 道同类新题（不看资料），记录是否成功。",
        "验证任务：1 周后混合复习时独立完成 2 道相关题，观察独立完成率是否提升。",
    ]
    return {"suggestions": suggestions, "verification_tasks": verification}
