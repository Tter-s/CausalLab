"""设置与 AI 配置测试：Key 加密、掩码、预算闸门、连通性测试。"""
from __future__ import annotations

from app.services.crypto import decrypt_secret, encrypt_secret, mask_secret


def test_crypto_roundtrip():
    token = encrypt_secret("sk-test-1234567890abcdef")
    assert token != "sk-test-1234567890abcdef"
    assert decrypt_secret(token) == "sk-test-1234567890abcdef"


def test_mask_secret():
    assert mask_secret("") == ""
    assert mask_secret("sk-1234567890abcd") == "sk-1****abcd"
    assert "x" not in mask_secret("x" * 6) or mask_secret("x" * 6) == "****"


def test_ai_config_roundtrip_and_masking(client):
    # 先重置为默认（其他测试可能改过配置）
    client.put("/api/settings/ai", json={"provider": "none", "model_id": "", "monthly_budget": 0})
    cfg = client.get("/api/settings/ai").json()
    assert cfg["provider"] == "none"

    # 保存带 Key 的配置
    r = client.put("/api/settings/ai", json={
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-very-secret-key-9876",
        "model_id": "用户自填的模型名",
        "temperature": 0.3,
        "max_tokens": 1024,
        "timeout_seconds": 45,
        "monthly_budget": 10,
    })
    assert r.status_code == 200
    saved = r.json()
    # Key 只能以掩码形式返回，绝不能出现原文
    assert saved["api_key_masked"].startswith("sk-v")
    assert "very-secret" not in saved["api_key_masked"]
    assert saved["model_id"] == "用户自填的模型名"

    # 不传 key 时保持原值
    r2 = client.put("/api/settings/ai", json={
        "provider": "deepseek", "base_url": "https://api.deepseek.com",
        "model_id": "另一个模型", "monthly_budget": 10,
    })
    assert r2.json()["api_key_masked"] == saved["api_key_masked"]

    # 恢复默认，避免影响其他测试
    client.put("/api/settings/ai", json={"provider": "none", "model_id": "", "monthly_budget": 0})


def test_budget_gate(client):
    """预算用尽时必须拒绝调用（402），且不影响非 AI 功能。"""
    import app.db as dbmod
    from app.models import AIUsageLog
    from app.services.base import utcnow

    # 直接往用量表塞满本月预算（不经过网络）
    session = dbmod.SessionLocal()
    session.add(AIUsageLog(provider="deepseek", model="m", task_type="general",
                           prompt_tokens=1000000, completion_tokens=0,
                           cost_estimated=999.0, latency_ms=1, ok=True, created_at=utcnow()))
    session.commit()
    session.close()

    client.put("/api/settings/ai", json={
        "provider": "openai-compat", "base_url": "http://127.0.0.1:9/v1",
        "api_key": "sk-x", "model_id": "m", "monthly_budget": 10,
    })
    s = client.post("/api/kd/subjects", json={"name": "预算学科"}).json()
    t = client.post("/api/kd/topics", json={"subject_id": s["id"], "name": "预算知识点"}).json()
    r = client.post("/api/ai/kd/diagnose", params={"topic_id": t["id"], "confirm_send": True})
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "ai_budget_exceeded"

    # 非 AI 功能不受影响
    assert client.get("/api/dashboard").status_code == 200

    # 清理：mock 不计费，但把 provider 改回 none 并清掉用量记录
    client.put("/api/settings/ai", json={"provider": "none", "model_id": "", "monthly_budget": 0})
    session = dbmod.SessionLocal()
    for row in session.query(AIUsageLog).all():
        session.delete(row)
    session.commit()
    session.close()


def test_test_connection_endpoint(client):
    client.put("/api/settings/ai", json={"provider": "mock", "model_id": "mock-1", "monthly_budget": 0})
    r = client.post("/api/settings/ai/test")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["provider"] == "mock"

    client.put("/api/settings/ai", json={"provider": "none", "model_id": "", "monthly_budget": 0})
    r2 = client.post("/api/settings/ai/test")
    assert r2.json()["ok"] is False
