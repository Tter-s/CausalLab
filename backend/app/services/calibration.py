"""预测校准分析与假设统计分析。"""
from __future__ import annotations

import math

CAVEAT = "校准分析基于你自己的概率预测记录；预测数量少时结果波动很大，仅供参考，不构成对你判断能力的评价。"


def brier_score(predictions: list[tuple[float, bool]]) -> float:
    if not predictions:
        return 0.0
    return sum((p - (1.0 if outcome else 0.0)) ** 2 for p, outcome in predictions) / len(predictions)


def calibration_bins(predictions: list[tuple[float, bool]], n_bins: int = 5) -> list[dict]:
    """把预测按概率分桶，对比平均预测概率与实际发生率。"""
    bins: list[dict] = []
    width = 1.0 / n_bins
    for i in range(n_bins):
        lower, upper = i * width, (i + 1) * width
        label = f"{lower:.0%}–{upper:.0%}"
        if i < n_bins - 1:
            group = [(p, o) for p, o in predictions if lower <= p < upper]
        else:
            group = [(p, o) for p, o in predictions if lower <= p <= upper]
        n = len(group)
        avg_predicted = sum(p for p, _ in group) / n if n else 0.0
        actual_rate = sum(1 for _, o in group if o) / n if n else 0.0
        bins.append(
            {
                "label": label,
                "lower": round(lower, 2),
                "upper": round(upper, 2),
                "n": n,
                "avg_predicted": round(avg_predicted, 3),
                "actual_rate": round(actual_rate, 3),
            }
        )
    return bins


def mean_std(values: list[float]) -> tuple[float | None, float | None]:
    n = len(values)
    if n == 0:
        return None, None
    mean = sum(values) / n
    if n < 2:
        return mean, None
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """皮尔逊相关系数。任务书要求不得把相关当因果——前端/接口都注明这一点。"""
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return round(cov / (sx * sy), 3)


HYP_LIMITATIONS = [
    "这是对你个人记录的描述性统计，不是随机对照实验。",
    "相关不等于因果：即使观察到关联，也可能由共同原因（如精力、任务难度）造成。",
    "样本量小的时候，少数极端值就能显著改变结论；请谨慎解释，并持续积累数据。",
    "观察期间其他条件（睡眠、材料难度等）可能已经变化，无法全部控制。",
]
