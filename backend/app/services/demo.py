"""演示数据生成器（明确标记为 Demo，不冒充真实记录）。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import (
    Attempt,
    Card,
    Decision,
    DecisionSnapshot,
    DecisionUpdate,
    Deck,
    Diagnosis,
    ExpGroup,
    Hypothesis,
    HypothesisObservation,
    ImprovementLoop,
    LoopStage,
    MemExperiment,
    Prediction,
    Project,
    ReviewState,
    StudyTask,
    Subject,
    Suggestion,
    Task,
    TaskEvent,
    Topic,
    TopicEdge,
)
from app.services import scheduling
from app.services.base import utcnow
from app.services.events import record_event


def seed_demo(db: Session) -> None:
    now = utcnow()

    # ---------- KD ----------
    subj = Subject(name="高等数学（演示）", description="演示用学科数据", color="#6366f1")
    db.add(subj)
    db.flush()
    t_limit = Topic(subject_id=subj.id, name="极限与连续", description="数列极限、函数极限、连续性")
    t_deriv = Topic(subject_id=subj.id, name="导数与微分", description="求导法则、隐函数求导")
    t_integr = Topic(subject_id=subj.id, name="不定积分", description="换元法、分部积分")
    db.add_all([t_limit, t_deriv, t_integr])
    db.flush()
    db.add_all([
        TopicEdge(from_topic_id=t_limit.id, to_topic_id=t_deriv.id, relation="prerequisite"),
        TopicEdge(from_topic_id=t_deriv.id, to_topic_id=t_integr.id, relation="prerequisite"),
    ])
    task1 = StudyTask(topic_id=t_integr.id, title="求 ∫x·e^x dx", question_text="用分部积分法求 ∫x·e^x dx")
    task2 = StudyTask(topic_id=t_integr.id, title="求 ∫ln(x) dx", question_text="用分部积分法求 ∫ln(x) dx")
    db.add_all([task1, task2])
    db.flush()
    demo_attempts = [
        (task1, False, "method_selection", False),
        (task2, False, "method_selection", False),
        (task1, True, "none", False),
        (task2, False, "method_selection", True),
    ]
    for i, (task, correct, cat, indep) in enumerate(demo_attempts):
        db.add(Attempt(task_id=task.id, topic_id=t_integr.id, correct=correct, error_category=cat,
                       independent=indep, occurred_at=now - timedelta(days=6 - i)))
    db.flush()
    diag = Diagnosis(
        topic_id=t_integr.id, category="method_selection", confidence=0.62,
        rationale="4 条记录中 3 次失败均标注为“方法选择困难”，其中 2 次未独立完成；"
                  "统计推断，非确诊。请结合实际体验判断。",
        evidence_attempts=[],
        alternatives=[
            {"category": "concept_gap", "likelihood": "low", "reason": "答对的那次说明基本概念可以理解。"},
            {"category": "transfer_failure", "likelihood": "medium", "reason": "独立完成的那次也失败，可能在陌生题上无法迁移方法。"},
        ],
        basis_attempt_count=4, source="rule", status="provisional",
    )
    db.add(diag)
    db.flush()
    sugg = Suggestion(diagnosis_id=diag.id, content="列出分部积分的适用条件（两类函数乘积），做题前先判断 u 和 dv 的选取。")
    db.add(sugg)
    t_integr.status = "weak"

    # ---------- ML ----------
    deck = Deck(name="英语核心词（演示）", description="演示用卡组")
    db.add(deck)
    db.flush()
    words = [("abandon", "放弃"), ("benevolent", "仁慈的"), ("candid", "坦率的"),
             ("diligent", "勤奋的"), ("eloquent", "雄辩的")]
    cards = []
    for front, back in words:
        c = Card(deck_id=deck.id, front=front, back=back, tags=["demo"])
        db.add(c)
        db.flush()
        db.add(ReviewState(card_id=c.id, fsrs_card=scheduling.new_card_dict(now), due_at=now, state_str="new"))
        cards.append(c)
    exp = MemExperiment(
        question="（演示）间隔复习与集中复习，48 小时后的记忆保持率有差异吗？",
        strategy_a="每天复习一次", strategy_b="考前集中复习",
        metric="delayed_test", delayed_test_days=7, notes="演示数据",
    )
    db.add(exp)
    db.flush()
    db.add_all([
        ExpGroup(experiment_id=exp.id, name="A", strategy="每天复习一次"),
        ExpGroup(experiment_id=exp.id, name="B", strategy="考前集中复习"),
    ])

    # ---------- DTM ----------
    d = Decision(
        title="（演示）考研还是就业",
        context="大三下学期，绩点中等，家庭希望稳定。",
        goals="两年后有更好的职业起点",
        options=[
            {"key": "A", "label": "全力考研", "description": "目标计算机专硕"},
            {"key": "B", "label": "直接就业", "description": "先工作再评估"},
        ],
        basis="对就业市场的了解有限；参考了两名学长的路径。",
        risks="考研失败的时间成本；就业起点可能较低。",
        review_at=now + timedelta(days=180),
    )
    db.add(d)
    db.flush()
    snap = DecisionSnapshot(
        decision_id=d.id, reason="created",
        payload={"title": d.title, "context": d.context, "goals": d.goals, "options": d.options,
                 "basis": d.basis, "risks": d.risks, "status": d.status, "review_at": None},
    )
    db.add(snap)
    db.add_all([
        Prediction(decision_id=d.id, statement="如果全力备考，初试过线的概率", option_key="A",
                   probability=0.6),
        Prediction(decision_id=d.id, statement="半年内拿到满意 offer 的概率", option_key="B",
                   probability=0.4),
    ])
    db.add(DecisionUpdate(decision_id=d.id, content="了解到目标院校今年缩招。", source="官网",
                          significance="major", occurred_at=now + timedelta(days=3)))

    # ---------- TA ----------
    p = Project(name="（演示）期末复习冲刺", description="三周复习计划")
    db.add(p)
    db.flush()
    t1 = Task(project_id=p.id, title="整理数据结构笔记", estimated_hours=6, status="done",
              started_at=now - timedelta(days=10), finished_at=now - timedelta(days=8), actual_hours=9.5)
    t2 = Task(project_id=p.id, title="刷操作系统真题", estimated_hours=8, status="blocked")
    t3 = Task(project_id=p.id, title="英语作文模板", estimated_hours=4, status="todo")
    db.add_all([t1, t2, t3])
    db.flush()
    db.add_all([
        TaskEvent(task_id=t1.id, type="interrupted", description="中途被社团事务打断两次",
                  duration_minutes=90, occurred_at=now - timedelta(days=9)),
        TaskEvent(task_id=t1.id, type="rework", description="笔记结构推倒重来一次",
                  occurred_at=now - timedelta(days=8.5)),
        TaskEvent(task_id=t2.id, type="blocked", description="真题答案册没到货，等快递",
                  duration_minutes=2880, occurred_at=now - timedelta(days=2)),
        TaskEvent(task_id=t2.id, type="requirement_change", description="老师划了新的重点范围",
                  occurred_at=now - timedelta(days=1)),
    ])

    # ---------- 假设 / 循环 ----------
    h = Hypothesis(
        statement="（演示）我在上午学习时独立完成率更高。",
        rationale="连续几次上午做题都比晚上顺利。",
        criteria={"support_if": "上午独立完成率比晚上高 15% 以上", "refute_if": "两组差异在 5% 以内"},
        status="testing",
    )
    db.add(h)
    db.flush()
    for i in range(8):
        db.add(HypothesisObservation(
            hypothesis_id=h.id,
            observed_at=now - timedelta(days=8 - i),
            value=0.8 if i % 2 == 0 else 0.5,
            context={"时段": "上午" if i % 2 == 0 else "晚上"},
            note="演示观察",
        ))
    loop = ImprovementLoop(
        title="（演示）减少刷题时的分心", problem="做题 20 分钟就想看手机，效率低。",
        current_stage="intervene", intervention="用番茄钟 + 手机放客厅，试用一周。",
    )
    db.add(loop)
    db.flush()
    db.add_all([
        LoopStage(loop_id=loop.id, stage="observe", content={"problem": "做题 20 分钟就想看手机"}),
        LoopStage(loop_id=loop.id, stage="hypothesize", content={"hypothesis": "分心主要来自手机在触手可及的地方"}),
        LoopStage(loop_id=loop.id, stage="intervene", content={"intervention": "番茄钟 + 手机放客厅"}),
    ])

    # ---------- 事件（让证据时间线有真实分布） ----------
    from app.services.events import record_event as _re
    _re(db, module="kd", event_type="attempt.recorded", ref_type="topic", ref_id=t_limit.id,
        title="记录答题（正确，独立）", occurred_at=now - timedelta(days=5))
    _re(db, module="kd", event_type="diagnosis.created", ref_type="topic", ref_id=t_integr.id,
        title="规则诊断：方法选择困难（置信度 62%）", occurred_at=now - timedelta(days=2), importance=2)
    _re(db, module="ml", event_type="ml.review", ref_type="card", ref_id=cards[0].id,
        title="复习卡片 abandon（评分 3，下次 3.5 天）", occurred_at=now - timedelta(days=1))
    _re(db, module="ml", event_type="experiment.created", ref_type="experiment", ref_id=exp.id,
        title="创建记忆实验：间隔 vs 集中复习", occurred_at=now - timedelta(days=3), importance=2)
    _re(db, module="dtm", event_type="decision.created", ref_type="decision", ref_id=d.id,
        title="创建决策：考研还是就业", occurred_at=now - timedelta(days=4), importance=2)
    _re(db, module="dtm", event_type="decision.update_added", ref_type="decision", ref_id=d.id,
        title="新信息（重大）：了解到目标院校今年缩招", occurred_at=now - timedelta(days=1), importance=2)
    _re(db, module="ta", event_type="task.status_changed", ref_type="task", ref_id=t1.id,
        title="任务「整理数据结构笔记」状态：doing → done", occurred_at=now - timedelta(days=8), importance=2)
    _re(db, module="ta", event_type="task.blocked", ref_type="task", ref_id=t2.id,
        title="任务「刷操作系统真题」记录阻塞：答案册没到货", occurred_at=now - timedelta(days=2), importance=2)
    _re(db, module="hyp", event_type="hypothesis.created", ref_type="hypothesis", ref_id=h.id,
        title="创建假设：上午学习独立完成率更高", occurred_at=now - timedelta(days=8), importance=2)
    _re(db, module="loop", event_type="loop.created", ref_type="loop", ref_id=loop.id,
        title="开启改进循环：减少刷题时的分心", occurred_at=now - timedelta(days=6), importance=2)
    record_event(db, module="sys", event_type="demo.seeded", ref_type="system", ref_id=0,
                 title="载入演示数据（非真实记录）", importance=3)
