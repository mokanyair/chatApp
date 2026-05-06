from prometheus_client import Counter, Gauge, Histogram

# ── Messages ──────────────────────────────────────────────────────────────────

messages_sent_total = Counter(
    "chat_messages_sent_total",
    "Total messages sent, by conversation type",
    ["conversation_type"],          # "direct" | "group"
)

# ── WebSocket connections ──────────────────────────────────────────────────────

active_ws_connections = Gauge(
    "chat_websocket_connections_active",
    "Number of currently open WebSocket connections",
)

ws_message_latency = Histogram(
    "chat_ws_message_latency_seconds",
    "Time from WebSocket message received to Redis publish",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# ── Conversations ─────────────────────────────────────────────────────────────

conversations_created_total = Counter(
    "chat_conversations_created_total",
    "Total conversations created, by type",
    ["type"],                       # "direct" | "group"
)

# ── Dependency health ─────────────────────────────────────────────────────────

dependency_healthy = Gauge(
    "dependency_healthy",
    "1 = reachable, 0 = unreachable",
    ["dependency"],                 # "mysql" | "redis"
)
