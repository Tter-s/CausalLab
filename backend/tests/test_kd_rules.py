"""KD 规则诊断引擎单元测试：重点验证“样本不足不下结论”护栏。"""
from __future__ import annotations

from app.services.kd_rules import AttemptFact, rule_diagnose, rule_suggestions


def test_single_failure_never_asserts_deficiency():
    """任务书硬约束：不得仅根据一道题或一次失败断言能力缺陷。"""
    result = rule_diagnose([AttemptFact(id=1, correct=False, error_category="concept_gap", independent=True)])
    assert result["category"] == "insufficient_data"
    assert result["confidence"] <= 0.25


def test_insufficient_with_two_fails():
    result = rule_diagnose([
        AttemptFact(id=1, correct=False, error_category="concept_gap", independent=True),
        AttemptFact(id=2, correct=True, error_category="none", independent=True),
    ])
    assert result["category"] == "insufficient_data"


def test_majority_category_wins():
    attempts = [
        AttemptFact(id=1, correct=False, error_category="method_selection", independent=True),
        AttemptFact(id=2, correct=False, error_category="method_selection", independent=True),
        AttemptFact(id=3, correct=False, error_category="concept_gap", independent=True),
        AttemptFact(id=4, correct=True, error_category="none", independent=True),
        AttemptFact(id=5, correct=True, error_category="none", independent=True),
    ]
    result = rule_diagnose(attempts)
    assert result["category"] == "method_selection"
    assert result["confidence"] > 0.5
    assert result["confidence"] <= 0.85
    assert len(result["alternatives"]) >= 1
    assert 1 in result["evidence_attempt_ids"]


def test_helped_correct_pattern_suggests_transfer():
    attempts = [
        AttemptFact(id=1, correct=False, error_category="method_selection", independent=True),
        AttemptFact(id=2, correct=False, error_category="method_selection", independent=True),
        AttemptFact(id=3, correct=True, error_category="none", independent=False),
        AttemptFact(id=4, correct=True, error_category="none", independent=False),
        AttemptFact(id=5, correct=False, error_category="method_selection", independent=True),
    ]
    result = rule_diagnose(attempts)
    alts = {a["category"] for a in result["alternatives"]}
    assert "transfer_failure" in alts


def test_suggestions_for_each_category():
    for cat in ("concept_gap", "retrieval_failure", "method_selection", "execution_error", "transfer_failure"):
        out = rule_suggestions(cat)
        assert len(out["suggestions"]) >= 1
        assert len(out["verification_tasks"]) >= 1
