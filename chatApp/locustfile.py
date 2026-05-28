# Load generator for chatapp
#
# Install deps:  pip install locust websocket-client
# Run headless:  locust -f locustfile.py --host https://<your-domain> \
#                       --users 50 --spawn-rate 5 --run-time 5m --headless
# Run with UI:   locust -f locustfile.py --host https://<your-domain>
#                then open http://localhost:8089

import base64
import json
import random
import string
import time

import websocket
from locust import HttpUser, between, events, task
from locust.exception import StopUser

# ── Helpers ───────────────────────────────────────────────────────────────────

CHAT_MESSAGES = [
    "Hey, how's it going?",
    "Did you see the latest update?",
    "Can we sync up later today?",
    "Just sent you the file",
    "Sounds good to me!",
    "Let me check and get back to you",
    "Can you share the details?",
    "Thanks for the heads up",
    "On it!",
    "What time works for you?",
    "I'll be there in 5",
    "Got it, thanks!",
    "Quick question — are we still on for tomorrow?",
    "Just finished the review",
    "Ping me when you're free",
]


def random_suffix(n=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def user_id_from_token(token: str) -> int:
    """Decode the JWT payload (no verification needed — we just need sub)."""
    payload = token.split(".")[1]
    payload += "=" * (4 - len(payload) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload))
    return int(data["sub"])


# ── Main user ─────────────────────────────────────────────────────────────────

class ChatAppUser(HttpUser):
    """
    Simulates a real user session:
      1. Register (once, on start)
      2. Login → get JWT
      3. Repeatedly: list conversations, open a WebSocket session and chat,
         send REST messages, browse conversation details
    """

    wait_time = between(1, 4)

    def on_start(self):
        self.token = None
        self.user_id = None
        self.conversation_ids = []
        self._register_and_login()
        self._bootstrap_conversation()

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _register_and_login(self):
        suffix = random_suffix()
        self.email = f"loadtest_{suffix}@loadtest.io"
        self.password = "LoadTest123!"
        username = f"lt_{suffix}"

        self.client.post(
            "/users/",
            json={"username": username, "email": self.email, "password": self.password},
            name="/users/ [register]",
        )

        with self.client.post(
            "/users/login",
            data={"username": self.email, "password": self.password},
            name="/users/login",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                self.token = resp.json()["access_token"]
                self.user_id = user_id_from_token(self.token)
            else:
                resp.failure(f"Login failed: {resp.status_code} {resp.text}")
                raise StopUser()

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    # ── Bootstrap ─────────────────────────────────────────────────────────────

    def _bootstrap_conversation(self):
        """Ensure this user has at least one conversation to work with."""
        # Try to start a direct conversation with user 1 (seed user).
        # Falls back gracefully if user 1 doesn't exist yet.
        with self.client.post(
            "/conversations/",
            json={"is_group": False, "participant_ids": [1], "title": None},
            headers=self._headers(),
            name="/conversations/ [create direct]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                self.conversation_ids.append(resp.json()["id"])
                resp.success()
            elif resp.status_code in (400, 404):
                resp.success()  # user 1 doesn't exist yet — that's fine
            else:
                resp.failure(f"Bootstrap conversation failed: {resp.status_code}")

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @task(5)
    def list_conversations(self):
        """Fetch the user's conversation list — most frequent action."""
        with self.client.get(
            "/conversations/",
            headers=self._headers(),
            name="/conversations/ [list]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                convs = resp.json()
                self.conversation_ids = [c["id"] for c in convs]
            else:
                resp.failure(f"{resp.status_code}")

    @task(4)
    def websocket_chat_session(self):
        """
        Open a WebSocket, send 2–5 messages with realistic pauses, then close.
        Models the dominant usage pattern of the app.
        """
        if not self.conversation_ids:
            return

        conv_id = random.choice(self.conversation_ids)
        ws_host = (
            self.host
            .replace("https://", "wss://")
            .replace("http://", "ws://")
        )
        url = f"{ws_host}/ws/{conv_id}?token={self.token}"

        start = time.perf_counter()
        try:
            ws = websocket.create_connection(url, timeout=10)
            for _ in range(random.randint(2, 5)):
                ws.send(json.dumps({"content": random.choice(CHAT_MESSAGES)}))
                time.sleep(random.uniform(0.3, 1.5))
            ws.close()
            elapsed_ms = (time.perf_counter() - start) * 1000
            events.request.fire(
                request_type="WebSocket",
                name="/ws/{conversation_id}",
                response_time=elapsed_ms,
                response_length=0,
                exception=None,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            events.request.fire(
                request_type="WebSocket",
                name="/ws/{conversation_id}",
                response_time=elapsed_ms,
                response_length=0,
                exception=exc,
            )

    @task(3)
    def send_message_rest(self):
        """Send a message via the REST endpoint (background tabs, API clients)."""
        if not self.conversation_ids:
            return
        conv_id = random.choice(self.conversation_ids)
        self.client.post(
            "/messages/",
            json={"conversation_id": conv_id, "content": random.choice(CHAT_MESSAGES)},
            headers=self._headers(),
            name="/messages/ [send]",
        )

    @task(2)
    def get_conversation_detail(self):
        """Fetch a single conversation — simulates opening a chat window."""
        if not self.conversation_ids:
            return
        conv_id = random.choice(self.conversation_ids)
        self.client.get(
            f"/conversations/{conv_id}",
            headers=self._headers(),
            name="/conversations/{id} [get]",
        )

    @task(1)
    def create_group_conversation(self):
        """
        Occasionally create a group chat with a few random existing users.
        Low weight — group creation is rare in real usage.
        """
        other_ids = random.sample(range(1, max(2, (self.user_id or 10))), k=min(2, (self.user_id or 2) - 1))
        with self.client.post(
            "/conversations/",
            json={
                "is_group": True,
                "participant_ids": other_ids,
                "title": f"Group {random_suffix(4)}",
            },
            headers=self._headers(),
            name="/conversations/ [create group]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                self.conversation_ids.append(resp.json()["id"])
                resp.success()
            elif resp.status_code in (400, 404):
                resp.success()
            else:
                resp.failure(f"{resp.status_code}")

    @task(1)
    def health_check(self):
        """Simulates ALB health probes and monitoring pings."""
        self.client.get("/health/live", name="/health/live")
        self.client.get("/health/ready", name="/health/ready")
