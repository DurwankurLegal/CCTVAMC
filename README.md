# CCTV AMC & Service Management Platform

A multi-tenant SaaS platform for CCTV service providers to manage AMC (Annual
Maintenance Contracts), service tickets, leads, invoices, and payments.

## Tech Stack

| Layer        | Technology                                                        |
| ------------ | ----------------------------------------------------------------- |
| **Backend**  | FastAPI (async), SQLAlchemy + asyncpg, PostgreSQL (Row-Level Security), Redis, Celery |
| **Frontend** | React + TypeScript, Vite, Ant Design, Redux Toolkit               |
| **Infra**    | Docker Compose, nginx reverse proxy                               |
| **Auth**     | JWT (tenant isolation enforced via PostgreSQL RLS)                |

## Architecture

```
┌─────────┐     ┌─────────────┐     ┌──────────────┐
│ Browser │────▶│    nginx    │────▶│  FastAPI API │
└─────────┘     │ (port 80)   │     │  (port 8000) │
                │  /  -> SPA  │     └──────┬───────┘
                │ /api-> API  │            │
                └─────────────┘     ┌──────▼───────┐   ┌─────────┐
                                    │  PostgreSQL  │   │  Redis  │
                                    │   (+ RLS)    │   │ + Celery│
                                    └──────────────┘   └─────────┘
```

Tenant isolation is enforced at the database level: every tenant's rows are
protected by PostgreSQL Row-Level Security, and `app.tenant_id` is set from the
JWT on every request — never from a client header.

## Prerequisites

- **Docker Desktop** (for Postgres, Redis, and full-stack runs)
- **Python 3.12+**
- **Node.js 20+**

## Quick Start (local development)

The fastest way to get everything running:

```bash
./start.sh
```

This script will:

1. Start Docker Desktop if it isn't already running
2. Bring up **Postgres** and **Redis** via `infra/docker-compose.dev.yml`
3. Run **Alembic migrations** (`alembic upgrade head`)
4. Start the **backend** (uvicorn) on `http://localhost:8000`
5. Start the **frontend** (Vite dev server) on `http://localhost:5173`

Press `Ctrl+C` to stop all services cleanly.

### First-time setup

```bash
# 1. Copy the environment template and fill in values
cp .env.example .env

# 2. Install backend dependencies
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cd ..

# 3. Install frontend dependencies
cd frontend
npm install
cd ..

# 4. Launch everything
./start.sh
```

Then open **http://localhost:5173**.

## Running the full stack in Docker (production-like)

To run the entire platform — including nginx serving the built frontend — use the
production compose file:

```bash
cd infra
docker compose up -d --build
```

The app is then served at **http://localhost** (port 80). nginx serves the built
SPA and proxies `/api/*` to the backend.

## Seeding the Database

A fresh database has no users. Create a starter tenant and an admin user with the
seed script (idempotent — safe to run more than once):

```bash
cd backend
source venv/bin/activate
python -m scripts.seed
```

Default login created: `admin@durwankur.ai` / `Admin@1234`
(override via `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` env vars).

## Environment Variables

All configuration lives in `.env` (never commit this file). See
[`.env.example`](.env.example) for the full list. Key variables:

| Variable            | Description                                  |
| ------------------- | -------------------------------------------- |
| `DATABASE_URL`      | Async Postgres connection string (asyncpg)   |
| `DATABASE_URL_SYNC` | Sync Postgres connection (Alembic migrations)|
| `REDIS_URL`         | Redis connection string                      |
| `JWT_SECRET_KEY`    | Secret for signing JWTs (use a long random value) |
| `CORS_ORIGINS`      | JSON array of allowed front-end origins      |

## Database Migrations

Schema changes are managed with Alembic. **Every schema change must ship as a new
migration committed alongside the code** — never edit shared databases by hand.

```bash
cd backend
alembic revision --autogenerate -m "describe your change"   # create a migration
alembic upgrade head                                          # apply migrations
alembic downgrade -1                                          # roll back one
```

## Testing

```bash
# Backend
cd backend
pytest tests/ --cov=app

# Frontend
cd frontend
npm run lint
npm test
```

## Project Structure

```
.
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/v1/    # Route handlers
│   │   ├── core/      # Config, database, security, deps
│   │   ├── models/    # SQLAlchemy models
│   │   ├── repositories/  # Data access (RLS-aware)
│   │   └── schemas/   # Pydantic schemas
│   ├── migrations/   # Alembic migrations
│   └── tests/
├── frontend/         # React + TypeScript SPA
│   └── src/
│       ├── pages/    # Dashboard, Customers, AMC, Tickets, Leads, Invoices, Payments
│       ├── store/    # Redux Toolkit slices
│       └── api/      # Axios client
├── mobile/           # Mobile app
├── infra/            # Docker Compose, nginx, DB init
└── start.sh          # Local dev launcher
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, commit
conventions, and the pull-request workflow.

## License

Proprietary — © Durwankur. All rights reserved.
