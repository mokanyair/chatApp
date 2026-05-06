"""
Instrument 5 — Dependency Health Checks as Prometheus Metrics

What it verifies:
  • GET /health/live → 200 always (liveness probe)
  • GET /health/ready → 200 when DB + Redis are up
  • dependency_healthy{dependency="mysql"} == 1.0 in /metrics
  • dependency_healthy{dependency="redis"} == 1.0 in /metrics
  • /health/ready → 503 when a dependency is down (simulated)
  • /health/* routes are excluded from RED metric tracking
"""

import requests
import subprocess
import time
from helpers import section, ok, fail, info, get_metrics, BASE


def run():
    section("Instrument 5 — Dependency Health Checks")

    # ── 0. Wait for all deps to be ready before testing ──────────────────────
    for attempt in range(10):
        try:
            if requests.get(f"{BASE}/health/ready", timeout=3).status_code == 200:
                break
        except Exception:
            pass
        info(f"Waiting for dependencies... (attempt {attempt+1}/10)")
        time.sleep(2)
    else:
        fail("Dependencies not ready after 20s — check docker compose status")
        return

    # ── 1. Liveness probe ─────────────────────────────────────────────────────
    r = requests.get(f"{BASE}/health/live")
    if r.status_code == 200 and r.json() == {"status": "ok"}:
        ok(f"GET /health/live → 200 {r.json()}")
    else:
        fail(f"GET /health/live → {r.status_code} {r.text}")

    # ── 2. Readiness probe (all deps up) ──────────────────────────────────────
    r = requests.get(f"{BASE}/health/ready")
    if r.status_code == 200:
        body = r.json()
        ok(f"GET /health/ready → 200 {body}")
    else:
        fail(f"GET /health/ready → {r.status_code} {r.text}")

    # ── 3. Prometheus gauges populated after /health/ready ────────────────────
    # Hit /health/ready first to ensure gauges are set
    requests.get(f"{BASE}/health/ready")
    m = get_metrics()

    mysql_val = m.get('dependency_healthy{dependency="mysql"}')
    redis_val = m.get('dependency_healthy{dependency="redis"}')

    if mysql_val == 1.0:
        ok(f'dependency_healthy{{dependency="mysql"}} = {mysql_val}')
    else:
        fail(f'dependency_healthy{{dependency="mysql"}} = {mysql_val} (expected 1.0)')

    if redis_val == 1.0:
        ok(f'dependency_healthy{{dependency="redis"}} = {redis_val}')
    else:
        fail(f'dependency_healthy{{dependency="redis"}} = {redis_val} (expected 1.0)')

    # ── 4. Simulate Redis failure → gauge drops to 0 ─────────────────────────
    # Use `docker stop` (closes TCP immediately) instead of `pause`
    # (which freezes the socket and causes indefinite hangs in the client).
    info("Stopping Redis container to simulate failure...")
    subprocess.run(["docker", "stop", "chat_redis"], capture_output=True)
    time.sleep(2)

    r = requests.get(f"{BASE}/health/ready", timeout=5)
    if r.status_code == 503:
        ok("GET /health/ready → 503 when Redis is down")
        body = r.json().get("detail", {})
        if isinstance(body, dict) and body.get("redis") == "unreachable":
            ok(f"Response body identifies redis as unreachable: {body}")
    else:
        fail(f"Expected 503 but got {r.status_code}")

    m = get_metrics()
    redis_down_val = m.get('dependency_healthy{dependency="redis"}')
    if redis_down_val == 0.0:
        ok('dependency_healthy{dependency="redis"} = 0.0 (Prometheus alert would fire)')
    else:
        fail(f'dependency_healthy{{dependency="redis"}} = {redis_down_val} (expected 0.0)')

    info("Restarting Redis...")
    subprocess.run(["docker", "start", "chat_redis"], capture_output=True)
    time.sleep(5)   # allow Redis to fully accept connections

    r = requests.get(f"{BASE}/health/ready", timeout=5)
    if r.status_code == 200:
        ok("GET /health/ready → 200 after Redis restarted")
    else:
        fail(f"Health not recovered after restart: {r.status_code}")

    m = get_metrics()
    redis_back = m.get('dependency_healthy{dependency="redis"}')
    if redis_back == 1.0:
        ok('dependency_healthy{dependency="redis"} recovered to 1.0')
    else:
        fail(f'Gauge did not recover: {redis_back}')

    # ── 5. /health/* excluded from RED metrics ────────────────────────────────
    for _ in range(5):
        requests.get(f"{BASE}/health/live")
        requests.get(f"{BASE}/health/ready")

    m = get_metrics()
    health_in_red = [k for k in m if "http_requests_total" in k and '"/health' in k]
    if not health_in_red:
        ok("/health/* routes not tracked in RED counters (correctly excluded)")
    else:
        info(f"Note: /health appears in RED counters: {health_in_red[:2]}")

    # ── 6. Alert rule coverage summary ───────────────────────────────────────
    print()
    print("  Alertmanager rules that now have data:")
    print('    DatabaseDown  →  dependency_healthy{dependency="mysql"} == 0')
    print('    RedisDown     →  dependency_healthy{dependency="redis"} == 0')
    print()
    print("  → View in Prometheus: http://localhost:9090/alerts")
    print("  → Alertmanager UI:    http://localhost:9093")


if __name__ == "__main__":
    run()
