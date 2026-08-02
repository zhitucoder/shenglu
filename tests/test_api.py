"""接口冒烟测试: 上传 -> 转写 -> 报告 -> 问答。
需要后端已启动, 且存在测试音频 /tmp/test_speech.mp3。
运行: pytest tests/test_api.py
"""
import os
import sys
import time

import httpx
import pytest

BASE = os.getenv("SL_TEST_BASE", "http://127.0.0.1:8000")
AUDIO = os.getenv("SL_TEST_AUDIO", "/tmp/test_speech.mp3")


@pytest.fixture(scope="module")
def client():
    return httpx.Client(base_url=BASE, timeout=120)


def _wait_transcript(client, session_id, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/api/audio/{session_id}")
        assert r.status_code == 200
        data = r.json()
        if data["status"] == "done":
            return data
        if data["status"] == "failed":
            pytest.fail(f"转写失败: {data.get('error')}")
        time.sleep(3)
    pytest.fail("转写超时")


def test_upload_and_transcribe(client):
    assert os.path.exists(AUDIO), f"缺少测试音频 {AUDIO}"
    with open(AUDIO, "rb") as f:
        r = client.post("/api/audio", files={"file": ("test.mp3", f, "audio/mpeg")})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "processing"
    result = _wait_transcript(client, data["id"])
    assert result["progress"] == 1.0
    assert result["transcript"] and "销售" in result["transcript"]


def test_report(client):
    with open(AUDIO, "rb") as f:
        sid = client.post("/api/audio", files={"file": ("t.mp3", f, "audio/mpeg")}).json()["id"]
    _wait_transcript(client, sid)
    r = client.post(f"/api/audio/{sid}/report")
    assert r.status_code == 200
    deadline = time.time() + 120
    while time.time() < deadline:
        data = client.get(f"/api/audio/{sid}/report").json()
        if data.get("report"):
            assert "总结" in data["report"] or "概述" in data["report"]
            return
        time.sleep(3)
    pytest.fail("报告生成超时")


def test_chat(client):
    with open(AUDIO, "rb") as f:
        sid = client.post("/api/audio", files={"file": ("t.mp3", f, "audio/mpeg")}).json()["id"]
    _wait_transcript(client, sid)
    r = client.post(f"/api/audio/{sid}/chat", json={"question": "卖出多少台设备?"})
    assert r.status_code == 200
    data = r.json()
    assert data["answer"]
    history = client.get(f"/api/audio/{sid}/chat").json()
    assert len(history) == 2


def test_history_list(client):
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1
    assert sessions[0]["id"] and sessions[0]["name"]


def test_rename_session(client):
    with open(AUDIO, "rb") as f:
        sid = client.post("/api/audio", files={"file": ("t.mp3", f, "audio/mpeg")}).json()["id"]
    r = client.patch(f"/api/audio/{sid}", json={"name": "重命名测试"})
    assert r.status_code == 200
    assert r.json()["name"] == "重命名测试"
    r = client.patch(f"/api/audio/{sid}", json={"name": "   "})
    assert r.status_code == 400


def test_downloads(client):
    with open(AUDIO, "rb") as f:
        sid = client.post("/api/audio", files={"file": ("t.mp3", f, "audio/mpeg")}).json()["id"]
    _wait_transcript(client, sid)
    r = client.get(f"/api/audio/{sid}/transcript/download")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "销售" in r.text
    client.post(f"/api/audio/{sid}/report")
    deadline = time.time() + 120
    report_ok = False
    while time.time() < deadline:
        if client.get(f"/api/audio/{sid}/report").json().get("report"):
            report_ok = True
            break
        time.sleep(3)
    assert report_ok
    r = client.get(f"/api/audio/{sid}/report/download")
    assert r.status_code == 200
    assert "总结" in r.text or "概述" in r.text

