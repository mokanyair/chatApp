"""Shared helpers used by all test scripts."""

import time
import requests

BASE = "http://localhost:8000"
METRICS_URL = f"{BASE}/metrics"


# ── Colour output ─────────────────────────────────────────────────────────────

def ok(msg):   print(f"  \033[92m✓\033[0m  {msg}")
def fail(msg): print(f"  \033[91m✗\033[0m  {msg}")
def info(msg): print(f"  \033[94m→\033[0m  {msg}")

def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ── Metrics parser ────────────────────────────────────────────────────────────

def parse_metrics(text: str) -> dict:
    """Return {metric_line: float} from Prometheus text format."""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.rsplit(" ", 1)
        if len(parts) == 2:
            try:
                result[parts[0]] = float(parts[1])
            except ValueError:
                pass
    return result

def get_metrics() -> dict:
    return parse_metrics(requests.get(METRICS_URL).text)

def metric_value(metrics: dict, name: str, labels: dict = None) -> float | None:
    """Look up a metric value, optionally filtering by labels."""
    if labels is None:
        return metrics.get(name)
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    key = f"{name}{{{label_str}}}"
    return metrics.get(key)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def register(username: str, email: str, password: str = "secret123") -> dict:
    r = requests.post(f"{BASE}/users/", json={
        "username": username, "email": email, "password": password
    })
    if r.status_code == 400:           # already exists — just login
        return login(email, password)
    r.raise_for_status()
    return login(email, password)

def login(email: str, password: str = "secret123") -> dict:
    r = requests.post(f"{BASE}/users/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()                    # {"access_token": ..., "token_type": "bearer"}

def auth_header(token_resp: dict) -> dict:
    return {"Authorization": f"Bearer {token_resp['access_token']}"}

def setup_two_users(prefix: str):
    """Register two users and create a direct conversation. Returns (token_a, token_b, conv_id)."""
    ts = int(time.time())
    a = register(f"{prefix}_a_{ts}", f"{prefix}_a_{ts}@test.com")
    b = register(f"{prefix}_b_{ts}", f"{prefix}_b_{ts}@test.com")

    # Get user B's id
    me = requests.get(f"{BASE}/users/login", json={})  # dummy — we need user id
    # Get id from creating user and reading response
    a_id = requests.post(f"{BASE}/users/", json={
        "username": f"{prefix}_ax_{ts}", "email": f"{prefix}_ax_{ts}@test.com", "password": "secret123"
    })
    # Easier: decode JWT sub claim
    import base64, json as _json
    def user_id_from_token(token: str) -> int:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(_json.loads(base64.b64decode(payload))["sub"])

    b_id = user_id_from_token(b["access_token"])

    conv = requests.post(
        f"{BASE}/conversations/",
        json={"participant_ids": [b_id], "is_group": False},
        headers=auth_header(a),
    )
    conv.raise_for_status()
    return a, b, conv.json()["id"]
