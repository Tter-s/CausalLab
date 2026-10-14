"""数据管理测试：导出导入往返、演示数据、清空。"""
from __future__ import annotations


def test_export_download_disposition(client):
    """桌面版导出：?download=1 带上 Content-Disposition（浏览器直接下载而非内联显示）。"""
    r = client.get("/api/data/export", params={"download": "1"})
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd and "causalab-export-" in cd
    assert r.json()["app"] == "CausaLab"


def test_export_import_roundtrip(client):
    # 造一点数据
    s = client.post("/api/kd/subjects", json={"name": "导出测试学科"}).json()
    client.post("/api/kd/topics", json={"subject_id": s["id"], "name": "导出测试知识点"})
    d = client.post("/api/dtm/decisions", json={"title": "导出测试决策"}).json()

    exported = client.get("/api/data/export").json()
    assert exported["app"] == "CausaLab"
    assert exported["schema_version"] == 1
    assert any(row["name"] == "导出测试知识点" for row in exported["tables"]["kd_topics"])
    n_decisions = len(exported["tables"]["dtm_decisions"])
    assert n_decisions >= 1

    # 导入（全量替换）
    r = client.post("/api/data/import", json=exported)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    # 数据仍在且完整
    assert client.get(f"/api/dtm/decisions/{d['id']}").status_code == 200
    topics = client.get("/api/kd/topics", params={"subject_id": s["id"]}).json()
    assert any(x["name"] == "导出测试知识点" for x in topics)

    # 非法文件拒绝
    bad = client.post("/api/data/import", json={"foo": "bar"})
    assert bad.status_code == 422


def test_demo_data_flagged(client):
    r = client.post("/api/data/demo")
    assert r.status_code == 200
    dash = client.get("/api/dashboard").json()
    assert dash["demo_mode"] is True

    # 演示数据覆盖各模块
    assert client.get("/api/kd/subjects").json()
    assert client.get("/api/ml/decks").json()
    assert client.get("/api/dtm/decisions").json()
    assert client.get("/api/ta/projects").json()
    assert client.get("/api/hypotheses").json()
    assert client.get("/api/loops").json()

    # 清除演示数据
    assert client.delete("/api/data/all").status_code == 200
    dash2 = client.get("/api/dashboard").json()
    assert dash2["demo_mode"] is False
    assert client.get("/api/kd/subjects").json() == []


def test_csv_exports(client):
    for path in ("/api/data/export/kd-attempts.csv", "/api/data/export/ml-reviews.csv"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
