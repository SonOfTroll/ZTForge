# ZTForge — File Guide & Interview Questions

## File-by-File Explanation

### Backend Core

| File | Purpose |
|------|---------|
| `app/main.py` | ASGI application factory. Assembles FastAPI with middleware (CORS, request-id, timing), registers all API routers, mounts Socket.io as an ASGI sub-application. The `create_app()` pattern enables testing with different configs. |
| `app/core/config.py` | Pydantic Settings class that validates all environment variables at startup. Fails fast if required config is missing. Feature flags control MVP features. `@lru_cache` ensures singleton behavior. |
| `app/core/security.py` | JWT validation against Keycloak's JWKS endpoint. Caches public keys with TTL to avoid per-request network calls. Handles key rotation by force-refreshing on kid mismatch. `RateLimiter` uses Redis sorted sets for sliding window counting. |
| `app/core/dependencies.py` | FastAPI dependency injection. Provides DB sessions (with auto-rollback on error), Redis connections, JWT auth extraction, rate limiting, and role-based access guards. The `require_role()` factory creates reusable guard dependencies. |
| `app/core/logging.py` | Structured logging via structlog. JSON output in production, colorized console in dev. Separate audit logger for security events that should never be filtered. |

### Models

| File | Purpose |
|------|---------|
| `models/user.py` | User synced from Keycloak on first login. No passwords stored — Keycloak owns authentication. Exists for foreign key relationships and app-specific metadata. |
| `models/canvas.py` | Core workspace. Nodes/edges stored as JSONB for schema flexibility. `version` field enables optimistic concurrency control — prevents lost updates from concurrent editors. |
| `models/policy.py` | Zero Trust policies attached to canvas edges. `rules` field stores structured conditions (require_mfa, require_compliant_device, etc.). `rego_content` stores the OPA-compatible policy text. |
| `models/template.py` | Community hub templates. Fork tracking via self-referential FK (`forked_from`). `fork_count` is eventually consistent — acceptable for a vanity counter. |

### Services

| File | Purpose |
|------|---------|
| `services/simulator.py` | Deterministic breach simulation engine. Builds adjacency graph from canvas, runs BFS from attacker's starting position, evaluates each edge's policy against attacker properties. 7 check rules (default deny, device compliance, MFA, credentials, time, microsegmentation, certificates). Returns typed `SimulationResult` with attack path, risk score, and recommendations. |
| `services/policy_engine.py` | OPA HTTP client with fail-closed design — denies by default when OPA is unreachable. Config exporters generate Rego, Pomerium YAML, Terraform HCL, and iptables from canvas state. |
| `services/collab_manager.py` | Socket.io event handler. Manages per-canvas rooms with presence tracking and cursor broadcasting. Cursor events use `volatile` (loss acceptable). Node/edge mutations are relayed to room members for real-time sync. |
| `services/enforcement.py` | MVP enforcement demo. Queries OPA for access decisions and emits audit logs. `sync_canvas_to_opa()` pushes canvas state as OPA data for runtime policy evaluation. |

### API Routes

| File | Purpose |
|------|---------|
| `api/v1/auth.py` | Keycloak OIDC token exchange. Exchanges authorization codes for access/refresh tokens. Syncs user to local DB on first login. |
| `api/v1/canvas.py` | Canvas CRUD with OCC. Rejects updates where client version doesn't match server version (409 Conflict). Validates nodes/edges structure before persisting. Access control: owner or admin for edits, public visibility check for reads. |
| `api/v1/policies.py` | Policy CRUD attached to canvases. Validates canvas ownership before allowing policy creation. |
| `api/v1/simulation.py` | Orchestrates breach simulation. Loads canvas + policies, instantiates `BreachSimulator`, returns typed result. Emits audit log with scenario and risk score. |
| `api/v1/hub.py` | Template marketplace. Fork creates deep copy with attribution. Export endpoint generates config in 4 formats. |
| `api/v1/users.py` | User profile endpoint. Returns DB user if synced, JWT claims if not. |

### Frontend

| File | Purpose |
|------|---------|
| `src/App.tsx` | React Router setup with 3 routes: Dashboard, Canvas, Hub. |
| `src/main.tsx` | React entry point. Renders App inside StrictMode. |
| `src/index.css` | TailwindCSS v4 import, design tokens (Inter/JetBrains Mono fonts), dark mode scrollbar styles, React Flow theme overrides. |
| `src/lib/types.ts` | TypeScript types mirroring backend Pydantic schemas. Shared across all components. Socket event payloads are typed here. |
| `src/lib/api.ts` | Fetch-based API client with typed methods. Token management via `setAccessToken()`. Error handling wraps HTTP errors in `ApiError`. |
| `src/lib/socket.ts` | Socket.io client singleton with reconnect logic. Typed emit helpers for all canvas events. Cursor events use `volatile` emission (UDP-like, loss acceptable). |
| `src/hooks/useCanvas.ts` | Main canvas state hook. Loads data from API, subscribes to Socket.io events for real-time sync, debounced auto-save (2s), and manages collaborator presence state. |
| `src/components/NodeTypes/index.tsx` | 6 custom React Flow nodes with distinct visual identities. Each node type has a unique color, icon, and handles. Compliance status shown as a colored dot. |
| `src/components/Canvas.tsx` | React Flow wrapper with minimap, background dots, controls. Positioned panels for canvas title, save status, and collaborators. |
| `src/components/Toolbar.tsx` | Node creation toolbar. Click adds a node at a random-ish position and broadcasts via Socket.io. |
| `src/components/SimulatorPanel.tsx` | Breach simulation controls. Scenario dropdown, run button, results display with risk score, attack path, and recommendations. |
| `src/components/PolicyHub.tsx` | Template browser with tag-based search, fork buttons, and loading skeletons. |
| `src/pages/Dashboard.tsx` | Landing page with asymmetric layout, canvas list, quick actions, and empty states. |
| `src/pages/CanvasPage.tsx` | Full-screen canvas with simulator side panel toggle and config export dropdown. |
| `src/pages/HubPage.tsx` | Community template marketplace page. |

### OPA Policies

| File | Purpose |
|------|---------|
| `opa/policies/base.rego` | Default deny rule. Requires authenticated session and valid role. |
| `opa/policies/breach_simulation.rego` | Simulation evaluation rules — mirrors the Python simulator logic in Rego. |
| `opa/policies/enforcement.rego` | Runtime enforcement. Checks incoming requests against canvas-defined policies stored in OPA data. |

### Infrastructure

| File | Purpose |
|------|---------|
| `docker-compose.yml` | 6-service stack: backend, frontend, postgres, redis, keycloak, opa. Health checks with dependency ordering. |
| `docker/keycloak/realm-export.json` | Pre-configured Keycloak realm with 4 roles and 3 demo users. |
| `backend/Dockerfile` | Python 3.12 slim with compiled deps. Serves via uvicorn. |
| `frontend/Dockerfile` | Multi-stage: Node build + nginx serve. |
| `frontend/nginx.conf` | SPA routing, API/WebSocket proxy, static asset caching. |

---

## Interview Questions

### Architecture & Design

1. **Why JSONB for canvas nodes/edges instead of relational tables?**
   React Flow's data model evolves. JSONB gives schema flexibility without migrations. Tradeoff: can't do relational queries on individual nodes (acceptable — we load the full canvas anyway).

2. **Why optimistic concurrency control instead of pessimistic locking?**
   Pessimistic locks block concurrent users. OCC allows parallel edits and only rejects on conflict. Better for collaborative UX. Version field + 409 Conflict response.

3. **Why Socket.io over raw WebSocket?**
   Rooms (per-canvas), automatic reconnection, fallback transports, and namespace support. Worth the dependency for collaboration features.

4. **Why OPA over a custom policy engine?**
   OPA is the industry standard for policy-as-code. Rego is purpose-built for access decisions. Using HTTP API keeps it loosely coupled. The simulator still has its own Python engine for performance — OPA is for runtime enforcement.

5. **Why Keycloak instead of custom auth?**
   Writing your own OIDC provider is a security liability. Keycloak handles password hashing, session management, MFA, and RBAC roles. The app only validates JWTs.

### Security

6. **How does rate limiting work?**
   Redis sorted set per user (keyed by JWT `sub`). Each request adds a timestamp entry. Entries outside the sliding window are trimmed. If count exceeds threshold (10/sec), return 429. Window is 1 second.

7. **What happens when OPA is unreachable?**
   Fail closed — return deny. This is intentional. An unreachable policy engine should not result in open access.

8. **How are JWKS keys cached?**
   Module-level `JWKSCache` dataclass with a 5-minute TTL. On kid mismatch (key rotation), force-refresh once then fail if still not found.

9. **How is input sanitized?**
   Pydantic v2 schemas with field validators (min/max length, regex patterns). Domain-specific validators for canvas structure (no self-loops, no orphaned edges, valid node types). Null byte stripping as defense in depth.

10. **What's the audit logging strategy?**
    Separate `ztforge.audit` logger that emits structured events for every state mutation: canvas CRUD, policy changes, simulation runs, auth events. Never filtered by log level. Can be routed to SIEM.

### Backend

11. **Explain the dependency injection pattern in FastAPI.**
    `Depends()` creates a dependency tree. `get_db` yields a session, `get_current_user` extracts JWT, `check_rate_limit` composes both. Role guards are factory functions that return dependency callables.

12. **How does the breach simulator work?**
    BFS traversal over the canvas graph. At each edge, 7 checks run sequentially: explicit allow, device compliance, MFA, credential validity, time restriction, microsegmentation, certificate validity. First failure blocks traversal. Risk score = sum of per-node risk contributions + coverage bonus.

13. **Why is the simulator deterministic?**
    Same inputs → same outputs. No randomness, no ML, no external state. This makes it auditable, testable, and explainable — critical for security tooling.

14. **How does the config export work?**
    Pure functions that transform canvas state (nodes + edges + policies) into format-specific strings. Each exporter iterates edges, checks for allow policies, and generates the appropriate syntax (Rego rules, Pomerium routes, Terraform resources, iptables commands).

### Frontend

15. **How does real-time collaboration sync work?**
    Hybrid approach: REST API for durable state (canvas CRUD), Socket.io for ephemeral state (cursors, presence) and real-time relay (node/edge changes). `useCanvas` hook manages both. Auto-save debounced at 2 seconds.

16. **What's the optimistic UI strategy?**
    Apply changes locally immediately (React state), broadcast via Socket.io for other clients, then persist via API. On API failure (version conflict), the change remains locally but isn't saved — user can retry. No hard rollback for MVP.

17. **How are React Flow node types customized?**
    `nodeTypes` registry maps type strings to React components. Each component receives `NodeProps` with typed `data`. Custom handles, icons, and colors per type. Compliance status shown as a colored indicator dot.

### DevOps & Deployment

18. **Why Docker Compose and not Kubernetes?**
    Target audience includes homelabbers and small teams. Compose is one command. K8s is overkill for MVP. The architecture (stateless backend, external DB/cache) is K8s-ready when needed.

19. **How do health checks work in the compose stack?**
    Each service has a health check command (pg_isready, redis-cli ping, wget OPA, HTTP to Keycloak). Backend depends on all services being healthy before starting. This prevents race conditions during cold start.

20. **How would you scale this to 1000 concurrent users?**
    - Horizontal backend scaling (multiple uvicorn workers behind a load balancer)
    - Redis adapter for Socket.io (already supported) to share rooms across processes
    - Read replicas for Postgres
    - CDN for frontend static assets
    - Connection pooling (already configured in SQLAlchemy)

### System Design

21. **How would you implement undo/redo?**
    Command pattern — each canvas mutation creates a reversible command object. Store a stack of commands per session. Undo pops and applies the inverse. Persist snapshots at save points.

22. **How would you add multi-tenant isolation?**
    Organization table with FK to users and canvases. Row-level security in Postgres. Tenant ID extracted from JWT and injected into every query via SQLAlchemy events.

23. **How would you handle offline mode?**
    IndexedDB for local canvas state. Service worker for static assets. Conflict resolution queue that replays changes on reconnect. CRDTs for concurrent edits (Yjs/Automerge).

24. **What's missing for production readiness?**
    - Secret rotation (Vault integration)
    - E2E tests (Playwright)
    - Monitoring (Prometheus + Grafana)
    - Backup strategy for Postgres
    - Rate limiting at reverse proxy level
    - CSP headers
    - Input sanitization for Rego content (OPA query injection)
    - RBAC enforcement on Socket.io events (currently unauthenticated)
