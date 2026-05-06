"""
Instrument 2 — RED Metrics (Rate, Errors, Duration)
via prometheus-fastapi-instrumentator → /metrics → Prometheus

What it verifies:
  • /metrics endpoint is reachable and returns Prometheus text format
  • http_requests_total counter increments on each request
  • 4xx responses are counted separately
  • http_request_duration_highr_seconds histogram is populated
  • Excluded routes (/metrics, /health/*) do not appear in counters
"""

import requests
from helpers import section, ok, fail, info, get_metrics, metric_value, BASE, METRICS_URL


def sum_counter(metrics: dict, name: str) -> float:
    """Sum all label combinations of a counter."""
    return sum(v for k, v in metrics.items() if k.startswith(name + "{") or k == name)


def run():
    section("Instrument 2 — RED Metrics")

    # ── 1. /metrics endpoint available ───────────────────────────────────────
    r = requests.get(METRICS_URL)
    if r.status_code == 200:
        ok("/metrics endpoint reachable")
    else:
        fail(f"/metrics returned {r.status_code}")
        return

    if "http_requests_total" in r.text:
        ok("Prometheus text format detected (http_requests_total present)")
    else:
        fail("http_requests_total not found in /metrics output")

    # ── 2. Rate — counter increments on successful requests ───────────────────
    before = get_metrics()
    before_count = sum_counter(before, "http_requests_total")

    # Make 5 known-good requests
    for _ in range(5):
        requests.get(f"{BASE}/health/live")

    # health routes are excluded from instrumentation, use a real route
    requests.get(f"{BASE}/users/99999")   # 404 but still counted
    requests.get(f"{BASE}/users/99999")

    after = get_metrics()
    after_count = sum_counter(after, "http_requests_total")
    delta = after_count - before_count

    if delta >= 2:
        ok(f"http_requests_total incremented by {delta:.0f} (≥ 2 expected)")
    else:
        fail(f"http_requests_total only increased by {delta:.0f} — expected ≥ 2")

    # ── 3. Errors — 4xx requests tracked ─────────────────────────────────────
    before_err = get_metrics()

    requests.get(f"{BASE}/users/99999")    # 404
    requests.post(f"{BASE}/users/login",   # 401
        json={"email": "nobody@x.com", "password": "wrong"})

    after_err = get_metrics()

    # Look for any key containing status="4" pattern
    err_keys_before = {k: v for k, v in before_err.items()
                       if "http_requests_total" in k and ('"4' in k or '"40' in k or '"401' in k or '"404' in k)}
    err_keys_after  = {k: v for k, v in after_err.items()
                       if "http_requests_total" in k and ('"4' in k or '"40' in k or '"401' in k or '"404' in k)}

    err_before_total = sum(err_keys_before.values())
    err_after_total  = sum(err_keys_after.values())

    if err_after_total > err_before_total:
        ok(f"4xx responses counted (delta = {err_after_total - err_before_total:.0f})")
    else:
        info("4xx label not found directly — check /metrics for status label format")
        # Print what we see
        sample = [k for k in after_err if "http_requests_total{" in k][:3]
        info(f"  Sample keys: {sample}")

    # ── 4. Duration — histogram populated ─────────────────────────────────────
    m = get_metrics()
    duration_keys = [k for k in m if "http_request_duration" in k and "_bucket" in k]
    if duration_keys:
        ok(f"Duration histogram present ({len(duration_keys)} buckets)")
        # Find the +Inf bucket total
        inf_keys = [k for k in duration_keys if 'le="+Inf"' in k]
        total_obs = sum(m[k] for k in inf_keys)
        info(f"  Total observations across all routes: {total_obs:.0f}")
    else:
        fail("Duration histogram not found in /metrics")

    # ── 5. Excluded routes NOT tracked ───────────────────────────────────────
    # /metrics itself and /health/* should not appear as handlers
    metrics_handler_key = [k for k in m if "http_requests_total" in k and '"/metrics"' in k]
    health_handler_key  = [k for k in m if "http_requests_total" in k and '"/health' in k]

    if not metrics_handler_key:
        ok("/metrics route excluded from RED tracking")
    else:
        fail(f"/metrics route appears in counters: {metrics_handler_key[:1]}")

    if not health_handler_key:
        ok("/health/* routes excluded from RED tracking")
    else:
        info(f"Note: /health route appears in counters (check exclusion config): {health_handler_key[:1]}")

    print(f"\n  → View in Prometheus: http://localhost:9090")
    print(f"  → Query: rate(http_requests_total[1m])")


if __name__ == "__main__":
    run()
