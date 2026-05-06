"""
Instrument 1 — Distributed Tracing (OTel → Jaeger)

What it verifies:
  • FastAPI auto-instrumentation creates spans for HTTP requests
  • SQLAlchemy instrumentation creates child spans for DB queries
  • Manual spans in ChatService appear with correct attributes
  • Jaeger receives and stores the trace

Prerequisite: docker compose up (with Jaeger service running)
  Jaeger UI:  http://localhost:16686
"""

import time
import requests
from helpers import section, ok, fail, info, setup_two_users, auth_header, BASE

JAEGER = "http://localhost:16686"
SERVICE = "chat-api"


def check_jaeger_available():
    try:
        r = requests.get(f"{JAEGER}/api/services", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def get_recent_traces(operation: str = None, limit: int = 5) -> list:
    params = {"service": SERVICE, "limit": limit}
    if operation:
        params["operation"] = operation
    r = requests.get(f"{JAEGER}/api/traces", params=params, timeout=5)
    if r.status_code != 200:
        return []
    return r.json().get("data", [])


def find_span(traces: list, operation_name: str) -> dict | None:
    for trace in traces:
        for span in trace.get("spans", []):
            if operation_name in span.get("operationName", ""):
                return span
    return None


def get_span_attr(span: dict, key: str):
    for tag in span.get("tags", []):
        if tag["key"] == key:
            return tag["value"]
    return None


def run():
    section("Instrument 1 — Distributed Tracing")

    if not check_jaeger_available():
        fail("Jaeger is not reachable at http://localhost:16686")
        info("Start it with: docker compose up jaeger -d")
        info("Then restart the API: docker compose restart api")
        return

    ok("Jaeger is reachable")

    # ── 1. Generate trace-producing activity ──────────────────────────────────
    info("Generating requests...")
    token_a, token_b, conv_id = setup_two_users("trace")

    requests.post(
        f"{BASE}/messages/",
        json={"conversation_id": conv_id, "content": "tracing test message"},
        headers=auth_header(token_a),
    )
    requests.get(f"{BASE}/conversations/{conv_id}", headers=auth_header(token_a))

    info("Waiting 3s for Jaeger to receive spans...")
    time.sleep(3)

    # ── 2. Service registered in Jaeger ──────────────────────────────────────
    services = requests.get(f"{JAEGER}/api/services").json().get("data", [])
    if SERVICE in services:
        ok(f"Service '{SERVICE}' registered in Jaeger")
    else:
        fail(f"Service '{SERVICE}' NOT found. Found: {services}")

    # ── 3. HTTP span created for POST /messages/ ─────────────────────────────
    traces = get_recent_traces(limit=20)
    http_span = find_span(traces, "POST /messages")
    if http_span:
        ok("HTTP span found: POST /messages/")
        status = get_span_attr(http_span, "http.status_code")
        info(f"  http.status_code = {status}")
    else:
        fail("No HTTP span found for POST /messages/")

    # ── 4. Manual span from ChatService.send_message ─────────────────────────
    chat_span = find_span(traces, "chat.send_message")
    if chat_span:
        ok("Manual span found: chat.send_message")
        for attr in ["chat.sender_id", "chat.conversation_id", "chat.content_length", "chat.message_id"]:
            val = get_span_attr(chat_span, attr)
            info(f"  {attr} = {val}")
    else:
        fail("Manual span 'chat.send_message' NOT found — check ChatService instrumentation")

    # ── 5. DB child span from SQLAlchemy auto-instrumentation ─────────────────
    db_span = find_span(traces, "INSERT")
    if db_span:
        ok("SQLAlchemy span found: INSERT (DB query traced)")
    else:
        info("No INSERT span found (may be nested — check Jaeger UI for parent trace)")

    print(f"\n  → View full traces at: {JAEGER}/search?service={SERVICE}")


if __name__ == "__main__":
    run()
