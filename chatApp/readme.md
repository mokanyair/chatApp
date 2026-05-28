
Phase2:
1. WebSockets + Redis pub/sub — makes it a real chat app
2. Horizontal scaling — 2-3 instances behind nginx
3. Read replica — offload heavy read queries

Consideration: When you hit the ceiling of horizontal monolith scaling then evaluate splitting. By then you'll   
  know exactly which service needs independent scaling (almost certainly the message delivery layer, not the user or conversation
   CRUD).

   ──────────────────────────┬───────────────────────────────┬────────────┐
  │         Approach         │   Handles (rough estimate)    │ Complexity │                                                      
  ├──────────────────────────┼───────────────────────────────┼────────────┤                                                      
  │ Current monolith         │ ~500 req/s                    │ Low        │
  ├──────────────────────────┼───────────────────────────────┼────────────┤                                                      
  │ + Redis caching          │ ~2,000 req/s                  │ Low        │
  ├──────────────────────────┼───────────────────────────────┼────────────┤                                                      
  │ + 3 horizontal instances │ ~5,000 req/s                  │ Low-Medium │
  ├──────────────────────────┼───────────────────────────────┼────────────┤                                                      
  │ + read replica           │ ~10,000 req/s                 │ Medium     │
  ├──────────────────────────┼───────────────────────────────┼────────────┤                                                      
  │ Microservices            │ same ceiling, more ops burden │ High       │
  └──────────────────────────┴───────────────────────────────┴────────────┘      
