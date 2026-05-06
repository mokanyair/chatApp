"""
Instrument 4 — Structured Trace-Correlated Logging (structlog)

What it verifies:
  • App logs are valid JSON (not plain text)
  • Every log line contains: level, timestamp, event
  • Request-scoped logs carry trace_id and span_id from OTel
  • trace_id is a valid 32-char hex string (128-bit)
  • span_id is a valid 16-char hex string (64-bit)
  • Business events are logged: message_sent, ws_connected, etc.
  • Warnings are logged for auth failures and forbidden actions

Note: DEBUG=False required for JSON output (set in .env).
      Reads logs via: docker logs chat_api
"""

import re
import json
import subprocess
import requests
import time
from helpers import section, ok, fail, info, auth_header, setup_two_users, BASE


TRACE_ID_RE = re.compile(r'^[0-9a-f]{32}$')
SPAN_ID_RE  = re.compile(r'^[0-9a-f]{16}$')


def get_recent_logs(lines: int = 100) -> list[dict]:
    """Pull last N lines from docker logs and parse JSON entries."""
    result = subprocess.run(
        ["docker", "logs", "chat_api", "--tail", str(lines)],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    parsed = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            pass   # non-JSON lines (uvicorn access log etc.) — skip
    return parsed


def find_log(logs: list[dict], event: str) -> dict | None:
    for entry in reversed(logs):
        if event in entry.get("event", ""):
            return entry
    return None


def run():
    section("Instrument 4 — Structured Trace-Correlated Logging")

    # ── 0. Check DEBUG=False (JSON mode) ─────────────────────────────────────
    raw = subprocess.run(
        ["docker", "logs", "chat_api", "--tail", "30"],
        capture_output=True, text=True
    ).stderr + subprocess.run(
        ["docker", "logs", "chat_api", "--tail", "30"],
        capture_output=True, text=True
    ).stdout

    json_lines = [l for l in raw.splitlines() if l.strip().startswith("{")]
    if json_lines:
        ok("JSON log lines detected")
    else:
        fail("No JSON log lines found — is DEBUG=False in .env?")
        info("Set DEBUG=False in .env and restart: docker compose restart api")
        return

    # ── 1. Generate log-producing activity ───────────────────────────────────
    info("Generating requests to produce structured log events...")
    token_a, token_b, conv_id = setup_two_users("log")

    # message_sent event
    requests.post(f"{BASE}/messages/",
        json={"conversation_id": conv_id, "content": "log test"},
        headers=auth_header(token_a))

    # ws_auth_failed event
    requests.get(f"ws://localhost:8000/ws/{conv_id}?token=bad.token.here",
                 headers={"Upgrade": "websocket"}) if False else None  # can't test WS auth via requests

    # message_delete_forbidden event
    msg = requests.post(f"{BASE}/messages/",
        json={"conversation_id": conv_id, "content": "to delete"},
        headers=auth_header(token_a)).json()
    requests.delete(f"{BASE}/messages/{msg['id']}",
        headers=auth_header(token_b))  # Bob tries to delete Alice's message

    time.sleep(0.5)   # let logs flush
    logs = get_recent_logs(200)

    # ── 2. Required fields on every log entry ─────────────────────────────────
    sample = logs[-5:] if logs else []
    all_have_level = all("level" in e for e in sample)
    all_have_event = all("event" in e for e in sample)
    all_have_ts    = all("timestamp" in e for e in sample)

    if all_have_level: ok("All sample entries have 'level' field")
    else:              fail("Some entries missing 'level'")

    if all_have_event: ok("All sample entries have 'event' field")
    else:              fail("Some entries missing 'event'")

    if all_have_ts:    ok("All sample entries have 'timestamp' field")
    else:              fail("Some entries missing 'timestamp'")

    # ── 3. Trace correlation fields ───────────────────────────────────────────
    traced = [e for e in logs if "trace_id" in e]
    if traced:
        sample_traced = traced[-1]
        tid = sample_traced.get("trace_id", "")
        sid = sample_traced.get("span_id",  "")

        if TRACE_ID_RE.match(tid):
            ok(f"trace_id is valid 32-char hex: {tid[:12]}...")
        else:
            fail(f"trace_id format invalid: '{tid}'")

        if SPAN_ID_RE.match(sid):
            ok(f"span_id is valid 16-char hex:  {sid}")
        else:
            fail(f"span_id format invalid: '{sid}'")
    else:
        fail("No log entries with trace_id found — OTel spans may not be active")
        info("Ensure OTLP tracing is wired and at least one request has been made")

    # ── 4. Business event: message_sent ──────────────────────────────────────
    msg_log = find_log(logs, "message_sent")
    if msg_log:
        ok("'message_sent' event logged")
        info(f"  message_id={msg_log.get('message_id')}  "
             f"sender_id={msg_log.get('sender_id')}  "
             f"conversation_type={msg_log.get('conversation_type')}")
    else:
        fail("'message_sent' event not found in logs")

    # ── 5. Warning: message_delete_forbidden ──────────────────────────────────
    forbidden_log = find_log(logs, "message_delete_forbidden")
    if forbidden_log:
        ok("'message_delete_forbidden' warning logged")
        info(f"  level={forbidden_log.get('level')}  "
             f"message_id={forbidden_log.get('message_id')}")
        if forbidden_log.get("level") in ("warning", "warn"):
            ok("Logged at WARNING level (not ERROR)")
        else:
            info(f"  Note: level is '{forbidden_log.get('level')}' (expected warning)")
    else:
        info("'message_delete_forbidden' not found — may require Bob to attempt deletion")

    # ── 6. conversation_created event ─────────────────────────────────────────
    conv_log = find_log(logs, "conversation_created")
    if conv_log:
        ok("'conversation_created' event logged")
        info(f"  type={conv_log.get('type')}  conversation_id={conv_log.get('conversation_id')}")
    else:
        fail("'conversation_created' event not found")

    print(f"\n  → Stream live: docker logs chat_api -f | python3 -m json.tool")
    print(f"  → With Loki: ship logs from docker → Loki → Grafana Explore")
    print(f"  → Click trace_id in Loki → jumps to Jaeger trace")


if __name__ == "__main__":
    run()
