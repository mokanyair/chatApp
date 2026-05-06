"""
Run all 5 observability instrument tests in sequence.

Usage (from chatApp/ directory):
    cd tests && python run_all.py
"""

import sys
import time
import requests

sys.path.insert(0, ".")


def check_api():
    try:
        r = requests.get("http://localhost:8000/health/live", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


if not check_api():
    print("\n  API is not reachable at http://localhost:8000")
    print("  Start it first: docker compose up api -d\n")
    sys.exit(1)

print("\n" + "═" * 62)
print("  OBSERVABILITY TEST SUITE")
print("═" * 62)

import test_01_tracing
import test_02_red_metrics
import test_03_business_metrics
import test_04_logging
import test_05_health

tests = [
    ("Distributed Tracing",       test_01_tracing.run),
    ("RED Metrics",               test_02_red_metrics.run),
    ("Business / Domain Metrics", test_03_business_metrics.run),
    ("Structured Logging",        test_04_logging.run),
    ("Health Checks",             test_05_health.run),
]

for name, fn in tests:
    try:
        fn()
    except Exception as e:
        print(f"\n  \033[91m✗\033[0m  {name} crashed: {e}")
    time.sleep(0.5)

print("\n" + "═" * 62)
print("  Done. Check the UIs:")
print("    Jaeger      → http://localhost:16686")
print("    Prometheus  → http://localhost:9090")
print("    Grafana     → http://localhost:3000  (admin / admin)")
print("    Alertmanager→ http://localhost:9093")
print("═" * 62 + "\n")
