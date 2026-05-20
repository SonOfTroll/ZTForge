# Contributing to ZTForge

Thanks for considering a contribution. ZTForge is a security tool — we hold contributions to a high bar.

## Development Setup

```bash
# Clone and start all services
git clone https://github.com/your-org/ztforge.git
cd ztforge
cp .env.example .env
docker compose up --build
```

Backend: http://localhost:8000  
Frontend: http://localhost:5173  
Keycloak: http://localhost:8080 (admin/admin)

## Branch Strategy

- `main` — stable, deployable
- `dev` — integration branch
- Feature branches: `feat/description`, `fix/description`

## Code Standards

### Backend (Python 3.12)
- Type hints on all function signatures
- Pydantic v2 for all request/response schemas
- `ruff` for linting, `black` for formatting
- Tests required for security-critical paths

### Frontend (TypeScript)
- Strict TypeScript — no `any` unless truly unavoidable (comment why)
- React Flow nodes must implement `NodeProps<T>` with typed data
- Socket events must use typed payloads from `lib/types.ts`

## Security Rules

- Every new API endpoint must validate JWT tokens via `get_current_user` dependency
- Input sanitization via Pydantic — never trust raw input
- No secrets in code. Use environment variables.
- Rate limiting is enforced globally. Do not bypass it.
- All state mutations must emit an audit log entry.

## Pull Request Process

1. Fork → branch → implement → test → PR
2. PR description must include: what changed, why, how to test
3. All CI checks must pass
4. Security-sensitive changes require review from a maintainer

## Reporting Vulnerabilities

Email security@ztforge.dev with details. Do not open public issues for security bugs.
