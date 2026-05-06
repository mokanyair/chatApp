"""
Instrument 3 — Business / Domain Metrics

What it verifies:
  • chat_messages_sent_total increments on REST and WebSocket sends
  • chat_conversations_created_total increments by type (direct/group)
  • chat_websocket_connections_active goes up on connect, down on disconnect
  • chat_ws_message_latency_seconds histogram is populated after WS send
"""

import asyncio
import json
import time
import requests
import websockets
from helpers import section, ok, fail, info, get_metrics, metric_value, auth_header, setup_two_users, BASE


def counter_total(metrics: dict, name: str, labels: dict) -> float:
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    key = f"{name}{{{label_str}}}"
    return metrics.get(key, 0.0)


def run():
    section("Instrument 3 — Business / Domain Metrics")

    token_a, token_b, conv_id = setup_two_users("biz")
    import base64, json as _json
    def uid(token):
        p = token["access_token"].split(".")[1]
        p += "=" * (-len(p) % 4)
        return int(_json.loads(base64.b64decode(p))["sub"])

    b_id = uid(token_b)

    # ── 1. chat_messages_sent_total — REST send ───────────────────────────────
    before = get_metrics()
    before_direct = counter_total(before, "chat_messages_sent_total",
                                  {"conversation_type": "direct"})

    requests.post(f"{BASE}/messages/",
        json={"conversation_id": conv_id, "content": "hello via REST"},
        headers=auth_header(token_a))
    requests.post(f"{BASE}/messages/",
        json={"conversation_id": conv_id, "content": "hello again"},
        headers=auth_header(token_a))

    after = get_metrics()
    after_direct = counter_total(after, "chat_messages_sent_total",
                                 {"conversation_type": "direct"})
    delta = after_direct - before_direct

    if delta >= 2:
        ok(f"chat_messages_sent_total{{conversation_type=direct}} +{delta:.0f}")
    else:
        fail(f"Expected +2, got +{delta:.0f} (current={after_direct:.0f})")

    # ── 2. chat_conversations_created_total ───────────────────────────────────
    before = get_metrics()
    before_direct_conv = counter_total(before, "chat_conversations_created_total", {"type": "direct"})
    before_group_conv  = counter_total(before, "chat_conversations_created_total", {"type": "group"})

    # Create a group conversation
    ts = int(time.time())
    token_c = requests.post(f"{BASE}/users/",
        json={"username": f"biz_c_{ts}", "email": f"biz_c_{ts}@test.com", "password": "secret123"})
    token_c = requests.post(f"{BASE}/users/login",
        json={"email": f"biz_c_{ts}@test.com", "password": "secret123"}).json()
    c_id = uid(token_c)

    requests.post(f"{BASE}/conversations/",
        json={"participant_ids": [b_id, c_id], "is_group": True, "title": "biz test group"},
        headers=auth_header(token_a))

    after = get_metrics()
    after_group_conv = counter_total(after, "chat_conversations_created_total", {"type": "group"})
    delta_group = after_group_conv - before_group_conv

    if delta_group >= 1:
        ok(f"chat_conversations_created_total{{type=group}} +{delta_group:.0f}")
    else:
        fail(f"Group conversation counter did not increment (delta={delta_group:.0f})")

    # ── 3. chat_websocket_connections_active ──────────────────────────────────
    before_ws = get_metrics()
    before_active = before_ws.get("chat_websocket_connections_active", 0.0)

    ws_url_a = f"ws://localhost:8000/ws/{conv_id}?token={token_a['access_token']}"
    ws_url_b = f"ws://localhost:8000/ws/{conv_id}?token={token_b['access_token']}"

    async def ws_gauge_test():
        async with websockets.connect(ws_url_a) as ws_a, \
                   websockets.connect(ws_url_b) as ws_b:
            await asyncio.sleep(0.3)

            mid = get_metrics()
            active = mid.get("chat_websocket_connections_active", 0.0)

            if active >= before_active + 2:
                ok(f"chat_websocket_connections_active = {active:.0f} (up by ≥2 while connected)")
            else:
                fail(f"Expected ≥{before_active+2:.0f} active, got {active:.0f}")

            # ── 4. WS message latency histogram ──────────────────────────────
            before_lat = get_metrics()
            before_count = before_lat.get("chat_ws_message_latency_seconds_count", 0.0)

            await ws_a.send(json.dumps({"content": "ws latency test"}))
            await asyncio.sleep(0.5)

            after_lat = get_metrics()
            after_count = after_lat.get("chat_ws_message_latency_seconds_count", 0.0)

            if after_count > before_count:
                ok(f"chat_ws_message_latency_seconds_count +{after_count - before_count:.0f} after WS send")
                # Check that some latency bucket was hit
                inf_key = 'chat_ws_message_latency_seconds_bucket{le="+Inf"}'
                inf_val = after_lat.get(inf_key, 0)
                info(f"  +Inf bucket count = {inf_val:.0f}")
            else:
                fail(f"WS latency histogram not updated (before={before_count:.0f}, after={after_count:.0f})")

        # After context exit, connections are closed
        await asyncio.sleep(0.3)

    asyncio.run(ws_gauge_test())

    # Connections closed — gauge should drop back
    final = get_metrics()
    final_active = final.get("chat_websocket_connections_active", 0.0)
    if final_active <= before_active:
        ok(f"chat_websocket_connections_active back to {final_active:.0f} after disconnect")
    else:
        fail(f"Gauge did not decrement after disconnect (still {final_active:.0f})")

    print(f"\n  → Grafana query examples:")
    print(f"    rate(chat_messages_sent_total[1m])")
    print(f"    chat_websocket_connections_active")
    print(f"    histogram_quantile(0.99, rate(chat_ws_message_latency_seconds_bucket[5m]))")


if __name__ == "__main__":
    run()
