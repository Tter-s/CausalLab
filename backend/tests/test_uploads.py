"""附件上传（题目 / 我的解答）测试。

覆盖：正常闭环、类型白名单、大小上限与残留清理、空文件、
module/ref_type/kind 校验、按实体隔离、下载内容一致、删除后磁盘文件同步删除、
stored_name 不外泄、以及文件名路径穿越无效。
"""
from __future__ import annotations

import pytest

from app.services.uploads import MAX_SIZE_BYTES, uploads_dir

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-payload" * 8


def _files_on_disk() -> set[str]:
    d = uploads_dir()
    return {p.name for p in d.iterdir() if p.is_file()}


@pytest.fixture()
def topic_id(client) -> int:
    """新建一个学科 + 知识点，返回知识点 id 作为附件挂载目标。"""
    sid = client.post("/api/kd/subjects", json={"name": "附件测试学科"}).json()["id"]
    tid = client.post("/api/kd/topics", json={"subject_id": sid, "name": "附件测试知识点"}).json()["id"]
    return tid


def _upload(client, topic_id: int, *, name="题目.png", kind="question", content=PNG_BYTES, module="kd", ref_type="topic"):
    return client.post(
        "/api/uploads",
        data={"module": module, "ref_type": ref_type, "ref_id": str(topic_id), "kind": kind, "note": "第一次作业"},
        files={"file": (name, content, "image/png")},
    )


def test_upload_list_download_delete_cycle(client, topic_id):
    before = _files_on_disk()

    r = _upload(client, topic_id)
    assert r.status_code == 201, r.text
    att = r.json()
    assert att["module"] == "kd"
    assert att["ref_type"] == "topic"
    assert att["ref_id"] == topic_id
    assert att["kind"] == "question"
    assert att["original_name"] == "题目.png"
    assert att["content_type"] == "image/png"  # 由扩展名推导，不信任客户端
    assert att["size_bytes"] == len(PNG_BYTES)
    assert att["note"] == "第一次作业"
    # 安全：磁盘内部文件名绝不出现在响应里
    assert "stored_name" not in att

    # 磁盘上确实落了一个文件，且是服务端生成的名字
    after = _files_on_disk()
    new_files = after - before
    assert len(new_files) == 1
    stored = next(iter(new_files))
    assert stored.endswith(".png")
    assert stored != "题目.png"

    # 列表按实体隔离
    listed = client.get(f"/api/uploads?module=kd&ref_type=topic&ref_id={topic_id}").json()
    assert [a["id"] for a in listed] == [att["id"]]
    other = client.get("/api/uploads?module=kd&ref_type=topic&ref_id=999999").json()
    assert other == []

    # 上传写入统一事件流
    evs = client.get(f"/api/timeline/entity?module=kd&ref_type=topic&ref_id={topic_id}").json()
    assert any(e["event_type"] == "attachment.uploaded" for e in evs)

    # 下载内容与上传一致
    dl = client.get(f"/api/uploads/{att['id']}/content")
    assert dl.status_code == 200
    assert dl.content == PNG_BYTES
    assert dl.headers["content-type"].startswith("image/png")

    # 删除后：记录消失、磁盘文件同步删除
    assert client.delete(f"/api/uploads/{att['id']}").status_code == 204
    assert client.get(f"/api/uploads?module=kd&ref_type=topic&ref_id={topic_id}").json() == []
    assert _files_on_disk() == before
    assert client.get(f"/api/uploads/{att['id']}/content").status_code == 404


def test_solution_kind_and_multiple_files(client, topic_id):
    a = _upload(client, topic_id, name="题目.png", kind="question")
    b = _upload(client, topic_id, name="我的解答.png", kind="solution")
    assert a.status_code == 201 and b.status_code == 201
    listed = client.get(f"/api/uploads?module=kd&ref_type=topic&ref_id={topic_id}").json()
    assert {x["kind"] for x in listed} == {"question", "solution"}


def test_reject_disallowed_extension(client, topic_id):
    before = _files_on_disk()
    r = _upload(client, topic_id, name="payload.exe", content=b"MZ\x90\x00")
    assert r.status_code == 422
    assert "不支持的文件类型" in r.json()["detail"]
    assert _files_on_disk() == before  # 不留残骸

    # 无扩展名同样拒绝
    assert _upload(client, topic_id, name="noext", content=b"x").status_code == 422


def test_reject_oversize_and_cleanup(client, topic_id, monkeypatch):
    monkeypatch.setattr("app.services.uploads.MAX_SIZE_BYTES", 1024)
    before = _files_on_disk()
    r = _upload(client, topic_id, name="big.png", content=b"a" * 4096)
    assert r.status_code == 413, r.text
    assert "上限" in r.json()["detail"]
    assert _files_on_disk() == before  # 超限后必须清掉半截文件
    monkeypatch.undo()
    assert MAX_SIZE_BYTES == 10 * 1024 * 1024  # 恢复常量，避免影响其他用例


def test_reject_empty_file(client, topic_id):
    before = _files_on_disk()
    r = _upload(client, topic_id, name="empty.png", content=b"")
    assert r.status_code == 422
    assert _files_on_disk() == before


@pytest.mark.parametrize(
    ("module", "ref_type", "kind"),
    [
        ("nope", "topic", "question"),
        ("kd", "nope", "question"),
        ("kd", "topic", "nope"),
    ],
)
def test_reject_invalid_scope(client, topic_id, module, ref_type, kind):
    r = _upload(client, topic_id, module=module, ref_type=ref_type, kind=kind)
    assert r.status_code == 422


def test_missing_file_field(client, topic_id):
    r = client.post("/api/uploads", data={"module": "kd", "ref_type": "topic", "ref_id": str(topic_id)})
    assert r.status_code == 422


def test_filename_traversal_is_harmless(client, topic_id):
    """文件名带 ../ 不能写出 uploads 目录之外。"""
    before = _files_on_disk()
    r = _upload(client, topic_id, name="../../evil.png")
    assert r.status_code == 201, r.text
    stored = next(iter(_files_on_disk() - before))
    assert "/" not in stored and "\\" not in stored and ".." not in stored
    # uploads 的上级（数据目录）里不应出现 evil.png
    assert not (uploads_dir().parent / "evil.png").exists()
    client.delete(f"/api/uploads/{r.json()['id']}")


def test_not_found_paths(client):
    assert client.get("/api/uploads/999999/content").status_code == 404
    assert client.delete("/api/uploads/999999").status_code == 404


def test_uploads_require_auth_when_enabled(client):
    """启用密码保护后，附件端点同样受中间件保护。"""
    password = "uploads-auth-pass"
    assert client.post("/api/auth/setup", json={"password": password}).status_code == 201
    try:
        assert client.get("/api/uploads?module=kd&ref_type=topic&ref_id=1").status_code == 401
        assert client.delete("/api/uploads/1").status_code == 401
    finally:
        assert client.post("/api/auth/disable", json={"password": password}).status_code == 200


def test_clear_all_data_removes_attachments_and_files(client, topic_id):
    """「清空业务数据」必须同时清掉附件记录与磁盘文件，不能留孤儿。"""
    assert _upload(client, topic_id).status_code == 201
    assert len(_files_on_disk()) >= 1

    assert client.delete("/api/data/all").status_code == 200

    assert client.get(f"/api/uploads?module=kd&ref_type=topic&ref_id={topic_id}").json() == []
    # 全量清空后附件目录应为空（含此前用例可能遗留的文件）
    assert _files_on_disk() == set()


def test_demo_reload_also_clears_attachments(client, topic_id):
    """载入演示数据会先清空业务数据，附件同样要被清掉。"""
    assert _upload(client, topic_id).status_code == 201
    assert client.post("/api/data/demo").status_code == 200
    assert client.get(f"/api/uploads?module=kd&ref_type=topic&ref_id={topic_id}").json() == []
    assert _files_on_disk() == set()
    # 收尾：演示数据会置 demo_mode，清掉以免影响其他用例
    assert client.delete("/api/data/all").status_code == 200
