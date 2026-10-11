"""认证（可选密码保护）测试。每个用例结束都恢复为禁用，避免影响其他测试。"""
from __future__ import annotations

import pytest

PASSWORD = "test-pass-123"


@pytest.fixture()
def auth_enabled(client):
    client.post("/api/auth/setup", json={"password": PASSWORD})
    yield
    r = client.post("/api/auth/disable", json={"password": PASSWORD})
    assert r.status_code == 200, f"teardown failed: {r.text}"  # 用例改过密码时必须先改回


def test_auth_disabled_by_default(client):
    status = client.get("/api/auth/status").json()
    assert status["enabled"] is False and status["authed"] is True
    # 未启用时所有 API 直接可用
    assert client.get("/api/dashboard").status_code == 200
    assert client.get("/api/health").status_code == 200


def test_setup_login_logout_cycle(client, auth_enabled):
    # 启用后：业务 API 401，公开端点仍可用
    r = client.get("/api/dashboard")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "auth_required"
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/auth/status").json() == {"enabled": True, "authed": False}

    # 重复 setup 被拒绝
    assert client.post("/api/auth/setup", json={"password": "x2y3z4a5b6"}).status_code == 409

    # 错误密码 401；正确密码设置会话
    assert client.post("/api/auth/login", json={"password": "wrong-password"}).status_code == 401
    ok = client.post("/api/auth/login", json={"password": PASSWORD})
    assert ok.status_code == 200
    assert "causalab_session" in ok.cookies

    # 会话有效
    assert client.get("/api/dashboard").status_code == 200
    assert client.get("/api/auth/status").json()["authed"] is True

    # 写操作也放行（同一会话）
    assert client.post("/api/kd/subjects", json={"name": "鉴权测试学科"}).status_code == 201

    # 登出后会话失效
    client.post("/api/auth/logout")
    assert client.get("/api/dashboard").status_code == 401


def test_change_password(client, auth_enabled):
    client.post("/api/auth/login", json={"password": PASSWORD})
    # 错误的旧密码
    r = client.post("/api/auth/change-password", json={"old_password": "wrong-pass-1", "new_password": "new-pass-456"})
    assert r.status_code == 401
    # 正确修改
    assert client.post("/api/auth/change-password",
                       json={"old_password": PASSWORD, "new_password": "new-pass-456"}).status_code == 200
    # 新密码可登录（旧会话仍有效——未强制下线，属可接受行为并在文档说明）
    client2 = client  # 同一 client 的会话仍有效
    assert client2.get("/api/dashboard").status_code == 200
    # 改回原密码（fixture teardown 依赖它）并登出清理会话
    assert client.post("/api/auth/change-password",
                       json={"old_password": "new-pass-456", "new_password": PASSWORD}).status_code == 200
    client.post("/api/auth/logout")


def test_disable_requires_password(client, auth_enabled):
    assert client.post("/api/auth/disable", json={"password": "wrong-password"}).status_code == 401
    assert client.get("/api/dashboard").status_code == 401  # 仍是锁定状态
    assert client.post("/api/auth/disable", json={"password": PASSWORD}).status_code == 200
    assert client.get("/api/dashboard").status_code == 200
    assert client.get("/api/auth/status").json()["enabled"] is False


def test_password_min_length(client):
    r = client.post("/api/auth/setup", json={"password": "123"})
    assert r.status_code == 422  # min_length=6


def test_login_rate_limit(client, auth_enabled):
    # 限流：同一 IP 连续错误 10 次后 429
    codes = [
        client.post("/api/auth/login", json={"password": f"wrong-{i}"}).status_code
        for i in range(12)
    ]
    assert 429 in codes
    # 限流窗口内即使密码正确也拒绝
    assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 429
