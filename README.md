# 皇甫谧数字人文平台 (Huangfu Mi Digital Humanities Platform)

中医经典智能研究平台 — AI-native digital humanities platform for TCM classical text research.

## Prerequisites

- **Docker** (Docker Desktop or Docker Engine + Compose v2)
- **Python ≥ 3.12** with `uv` (or pip + venv)
- **Node.js ≥ 22** with `pnpm` ≥ 10
- **PostgreSQL client** (`psql`) — optional, for debugging

Host-only dependencies (for development without Docker container builds):

```bash
# macOS
brew install python@3.12 node pnpm postgresql@16

# Verify
python3 --version   # ≥ 3.12
node --version      # ≥ 22
pnpm --version      # ≥ 10
docker compose version
```

## Quick Start (Development)

### 1. Clone and configure

```bash
git clone <repo-url> hfb
cd hfb

# .env is already tracked with safe development defaults.
# If .env does not exist, copy from the template:
cp .env.example .env
```

**Do not commit real secrets to `.env`.** The development defaults use well-known
passwords (`hfb:change-me`) that are only safe on `localhost`.

### 2. Check for port conflicts

Port `5432` must be free before starting. Check for conflicting containers or local
PostgreSQL instances:

```bash
lsof -i :5432              # macOS/Linux — should be empty
docker ps --filter publish=5432  # should show no containers
```

If something is already on port 5432, stop it first. The HFB Compose file maps
PostgreSQL to the host on 5432.

### 3. Start infrastructure (Docker)

```bash
docker compose -f docker-compose.dev.yml up -d postgres redis elasticsearch minio
```

Wait for all services to be healthy:

```bash
docker compose -f docker-compose.dev.yml ps
# All four services should show "(healthy)"
```

### 4. Initialize the database

```bash
# Run migrations
uv run alembic upgrade head

# Seed development baseline (RBAC, users, research data)
uv run python ../../scripts/init_dev_baseline.py
```

The baseline script creates:

- RBAC roles, permissions, and an admin user (username `admin` / password `admin123`)
- A researcher user (username `researcher` / password `researcher123`)
- 《针灸甲乙经》book, version (明代刻本), chapters, and passages
- Full-text document with chunks linked to passages
- Evidence + Citation chain: citations → evidences → passages → versions

This step is only needed on **first initialization** or after deleting the
Docker volume. The script is idempotent — safe to run multiple times.

### 5. Start the backend

```bash
cd apps/backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Verify:

```bash
curl -i http://127.0.0.1:8000/health   # → 200 OK
curl -i http://127.0.0.1:8000/ready    # → 200 OK (all services healthy)
```

### 6. Start the frontend

```bash
cd apps/frontend   # or from root: cd apps/frontend
pnpm install
pnpm dev           # Vite dev server on :5173
```

Verify:

```bash
curl -i http://127.0.0.1:5173/         # → 200 OK
curl -i http://127.0.0.1:5173/health   # → 200 (proxied to backend)
curl -i http://127.0.0.1:5173/ready    # → 200 (proxied to backend)
```

### 7. Stop

```bash
# Stop backend + frontend (Ctrl-C in their terminals), then:

docker compose -f docker-compose.dev.yml down
# Add -v to delete data volumes: docker compose -f docker-compose.dev.yml down -v
```

## One-Command Restart (after first initialization)

```bash
# Infrastructure
docker compose -f docker-compose.dev.yml up -d postgres redis elasticsearch minio

# Backend (terminal 1)
cd apps/backend && uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (terminal 2)
cd apps/frontend && pnpm dev
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Host (macOS / Linux)                               │
│                                                     │
│  ┌──────────┐   ┌───────────┐                      │
│  │ Backend  │   │ Frontend  │                      │
│  │ :8000    │   │ :5173     │                      │
│  │ (uvicorn)│   │ (Vite)    │                      │
│  └────┬─────┘   └───────────┘                      │
│       │  localhost:5432,6379,9200,9000              │
│       ▼                                             │
│  ┌─────────────────────────────────────────────┐    │
│  │ Docker (docker-compose.dev.yml)             │    │
│  │                                             │    │
│  │  postgres:5432  redis:6379                  │    │
│  │  elasticsearch:9200  minio:9000             │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

The `.env` file uses `localhost` because the backend runs on the host and
connects through Docker's port mappings. When running inside Docker
(`docker compose up backend`), the Compose file overrides hostnames to
Docker service names (`postgres`, `redis`, `elasticsearch`, `minio`).

## Credentials (Development)

| Service       | User         | Password        | Notes                             |
| ------------- | ------------ | --------------- | --------------------------------- |
| PostgreSQL    | `hfb`        | `change-me`     | Database: `hfb`                   |
| Redis         | —            | —               | No password in dev                |
| Elasticsearch | —            | —               | Security disabled in dev          |
| MinIO         | `minioadmin` | `minioadmin`    | Console on :9001                  |
| Admin Web UI  | `admin`      | `admin123`      | Created by `init_dev_baseline.py` |
| Researcher    | `researcher` | `researcher123` | Created by `init_dev_baseline.py` |

## Docker Image Availability

This project pulls images from Docker Hub (`docker.io`). If your network
environment intercepts TLS connections to `auth.docker.io` (e.g., corporate
proxy injecting certificates for `*.axzamy.xyz`), image pulls will fail with
`x509: certificate is valid for ... not auth.docker.io`.

**This is an external environment blocker, not a repository issue.**
Workarounds:

1. Use a network without TLS interception.
2. Pre-pull images from a mirror registry and re-tag them:
   ```bash
   docker pull docker.m.daocloud.io/pgvector/pgvector:pg16
   docker tag docker.m.daocloud.io/pgvector/pgvector:pg16 pgvector/pgvector:pg16
   # Repeat for redis:7-alpine, minio/minio:latest
   docker pull docker.elastic.co/elasticsearch/elasticsearch:8.17.0  # separate registry
   ```

The `backend` and `frontend` Docker images also require outbound HTTP access
to `deb.debian.org` during `apt-get` (Dockerfile build). If blocked, use the
host-native development path described above.

## Troubleshooting

### "password authentication failed for user hfb"

You are connecting to the wrong PostgreSQL instance. Check:

```bash
lsof -i :5432
docker ps --filter publish=5432
```

Stop any conflicting containers or local PostgreSQL services.

### "ConnectionRefusedError" on port 5432/6379/9200/9000

Docker services are not running:

```bash
docker compose -f docker-compose.dev.yml up -d postgres redis elasticsearch minio
```

### Alembic "relation already exists"

You already ran migrations. This is safe to ignore. Use `alembic stamp head`
to mark the current state without re-running.

### "the asyncio extension requires an async driver"

Do not override `DATABASE_URL` with a sync driver (`postgresql+psycopg2://`).
Use the default from Settings, or use `postgresql+asyncpg://` explicitly.

## API Documentation

When the backend is running with `DEBUG=true`:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## License

MIT
