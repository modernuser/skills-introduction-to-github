import sys
from pathlib import Path

from conftest import load


def test_silent_noop_without_webhook(workdir, monkeypatch, capsys):
    ns = load("notify_slack")
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["notify_slack.py", "briefing"])
    assert ns.main() == 0
    out = capsys.readouterr()
    assert "skipped" in out.out and "hooks.slack.com" not in out.out + out.err


def test_rejects_non_slack_url(workdir, monkeypatch, capsys):
    ns = load("notify_slack")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://evil.example.com/x")
    monkeypatch.setattr(sys, "argv", ["notify_slack.py", "moves"])
    called = []
    monkeypatch.setattr(ns.urllib.request, "urlopen",
                        lambda *a, **k: called.append(1))
    assert ns.main() == 0
    assert not called, "must never post to a non-Slack URL"


def test_payload_shape_and_truncation(workdir):
    ns = load("notify_slack")
    p = ns.build_payload("moves", "SNDK -10.79%")
    assert p["blocks"][0]["text"]["text"].startswith(":warning:")
    assert "SNDK -10.79%" in p["blocks"][1]["text"]["text"]
    assert "not advice" in p["blocks"][2]["elements"][0]["text"]
    long = ns.build_payload("briefing", "x" * 5000)
    assert "truncated" in long["blocks"][1]["text"]["text"]
    assert len(long["blocks"][1]["text"]["text"]) < 3000


def test_http_failure_tolerated_and_url_never_leaked(workdir, monkeypatch, capsys):
    ns = load("notify_slack")
    secret_url = "https://hooks.slack.com/" + "services-path-x"
    monkeypatch.setenv("SLACK_WEBHOOK_URL", secret_url)
    Path("body.md").write_text("hello")
    monkeypatch.setattr(sys, "argv", ["notify_slack.py", "briefing", "body.md"])

    def boom(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(ns.urllib.request, "urlopen", boom)
    assert ns.main() == 0                       # never fails the pipeline
    out = capsys.readouterr()
    assert "failed" in out.err
    assert "services-path-x" not in out.out + out.err


def test_successful_post(workdir, monkeypatch, capsys):
    ns = load("notify_slack")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/" + "svc")
    Path("body.md").write_text("briefing text")
    monkeypatch.setattr(sys, "argv", ["notify_slack.py", "briefing", "body.md"])
    sent = {}

    class FakeResp:
        def read(self):
            return b"ok"
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_open(req, timeout=0):
        import json as j
        sent.update(j.loads(req.data.decode()))
        return FakeResp()
    monkeypatch.setattr(ns.urllib.request, "urlopen", fake_open)
    assert ns.main() == 0
    assert "briefing text" in sent["blocks"][1]["text"]["text"]
    assert "sent" in capsys.readouterr().out
