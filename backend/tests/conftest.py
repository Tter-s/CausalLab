"""pytest 全局夹具：在任何 app 导入前把数据目录指到临时目录，保证测试隔离且不污染开发库。"""
from __future__ import annotations

import os
import tempfile

# 必须先于 app.* 导入设置环境变量
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="causalab_test_")
os.environ["CAUSALAB_DATA_DIR"] = _TEST_DATA_DIR

import shutil  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001
    # 必须先释放连接池：否则 Windows 上 SQLite 文件句柄未关闭，
    # rmtree 会删不掉 causalab.db，而 ignore_errors=True 会把失败吞掉，
    # 导致每次运行都在临时目录里漏下一个 causalab_test_* 目录。
    from app.db import engine

    engine.dispose()
    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)
