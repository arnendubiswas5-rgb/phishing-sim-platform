# Phishing Simulation Platform

A full-stack phishing simulation and security-awareness training platform for
**authorized** security-awareness programs and red-team exercises (the
GoPhish / KnowBe4 category of defensive tooling). It lets an organization run
controlled simulated-phishing campaigns against its own employees, deliver
training to anyone who interacts with a simulation, and report on results —
all scoped per tenant.

**Created by Arnendu Biswas &lt;arnendubiswas5@gmail.com&gt;**

> **Authorized use only.** This software is intended solely for simulated
> phishing against users who have consented to security-awareness testing
> within your own organization. Do not use it to target anyone without explicit
> authorization. See the [Ethical Use Disclaimer](#ethical-use-disclaimer).

## Live Demo

> ⚠️ This is a self-hosted tool. No public demo is available for security
> reasons — phishing-simulation platforms must run in an isolated environment.
> See [Deploy to Production](#deploy-to-production) to run your own instance.

## Features

- **Multi-tenant** — every record is scoped by `tenant_id`.
- **Campaigns** — build and launch simulated-phishing campaigns from reusable
  email templates and landing pages, targeting selected recipients.
- **Templates & landing pages** — full CRUD with live preview rendered against
  sample target data.
- **Tracking** — opens, clicks, and credential-submission events, with
  shortened tracking links.
- **Training** — training modules with quizzes, assignable to targets, plus a
  public training page.
- **Reporting** — per-campaign dashboards, timelines, and department breakdowns.
- **Security & compliance** — JWT auth, audit logging, rate limiting, and a
  scheduled purge of expired data.

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | FastAPI, SQLAlchemy (async), Celery |
| Datastores | PostgreSQL, Redis |
| Frontend | React, Vite, Tailwind CSS |
| Serving / Infra | Nginx, Docker |

## Architecture

All services are orchestrated with `docker-compose.yml`. Nginx is the single
entry point; it serves the built React app and reverse-proxies API and tracking
routes to the backend. The backend and the Celery worker share the same code
image and talk to PostgreSQL and Redis. Celery (via Redis as broker) handles
email sending and scheduled data purges.

```
                         ┌──────────────────────────┐
        Browser  ───────▶│   Nginx (gateway :8080)   │
                         └────────────┬──────────────┘
                   static app │       │ /api, /t, /s (proxy)
                   ┌──────────▼──┐   ┌─▼───────────────────┐
                   │  Frontend   │   │  Backend (FastAPI)  │
                   │  (React)    │   │                     │
                   └─────────────┘   └───┬─────────────┬───┘
                                         │             │
                                   ┌─────▼─────┐  ┌────▼────┐
                                   │ PostgreSQL│  │  Redis  │
                                   └─────▲─────┘  └────▲────┘
                                         │             │ broker / backend
                                   ┌─────┴─────────────┴───┐
                                   │   Celery worker       │
                                   │ (email send, purges)  │
                                   └───────────────────────┘
```

## Screenshots

<!-- TODO: Add screenshot of Dashboard -->
<!-- TODO: Add screenshot of Campaign Wizard -->
<!-- TODO: Add screenshot of Landing Page editor -->
<!-- TODO: Add screenshot of Reports -->

## Getting Started

### Prerequisites

- Docker Desktop (for PostgreSQL, Redis, and the optional Mailpit mail catcher)
- Python 3.12 and Node.js 20 (for running backend/frontend outside Docker)

### Run Locally (Development)

> The URLs in this section are **local development only**. They are not
> reachable from the internet and must never be used as production endpoints.

Run the whole stack with Docker:

```bash
# from the project root
cp .env.example .env    # then edit the values
docker compose up -d --build
```

The app is served through the nginx gateway at **http://localhost:8080**
(dev only).

Or run the services individually for a faster edit loop:

```bash
# 1. Start the datastores
docker compose up -d postgres redis

# 2. Backend
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Frontend (in another terminal)
cd frontend
npm install
npm run dev        # http://localhost:5173 (dev only)

# 4. Celery worker (needed for campaign sending)
cd backend
celery -A app.workers.email_worker.celery_app worker --loglevel=info --pool=solo
```

### Deploy to Production

The Docker images are production-ready and can run on any Docker-compatible
host — Railway, Render, Fly.io, AWS ECS, DigitalOcean, etc. A typical split-
service deployment runs five services: **PostgreSQL**, **Redis**, the
**backend** (FastAPI on `$PORT`), the **Celery worker** (same image, started
with `celery -A app.workers.email_worker.celery_app worker --loglevel=info`),
and the **frontend** (Nginx serving the built React app).

Notes for a split-service host:

- The backend normalizes a managed `postgres://` / `postgresql://` database URL
  to the async driver automatically, so the provider's injected `DATABASE_URL`
  works as-is.
- Run migrations on container start, e.g.
  `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
  (`backend/railway.json` already encodes this for Railway.)
- Build the frontend with `VITE_API_BASE_URL` set to the backend's public API
  root (e.g. `https://your-backend.example.com/api/v1`), and add that frontend
  origin to the backend's `CORS_ORIGINS`.

#### Production Environment Variables

These **must** be changed from their development defaults before going live:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs JWT access/refresh tokens. Use a new 32-byte random hex. |
| `ENCRYPTION_KEY` | Fernet key encrypting SMTP passwords / captured data at rest. Generate a fresh key. |
| `TRACKING_HMAC_SECRET` | Signs tracking-link UUIDs. Use a new 32-byte random hex. |
| `APP_BASE_URL` | Public HTTPS URL of the backend (used to build tracking links). |
| `ADMIN_PASSWORD` | Seeded admin password (with `ADMIN_EMAIL`). Use a strong value. |
| `SMTP_*` / SMTP profile | Real relay credentials — Mailpit does not exist in production. |
| `DATABASE_URL`, `REDIS_URL` | Point at the managed Postgres / Redis instances. |
| `ENVIRONMENT` | Set to `production`. |
| `CORS_ORIGINS` | The frontend's public origin(s). |

Generate secrets:

```bash
python -c "import secrets; print(secrets.token_hex(32))"          # SECRET_KEY / TRACKING_HMAC_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # ENCRYPTION_KEY
```

> #### ⚠️ `APP_BASE_URL` is critical
> When deploying, `APP_BASE_URL` must be the **public HTTPS URL of the
> backend**, never `localhost`. Tracking pixels, click links, and short links
> embedded in simulated emails are built from this value — if it points at
> localhost, opens/clicks/submissions from real inboxes will never register.

### Configuration

Copy `.env.example` to `.env` and fill in the values. `.env` is gitignored and
must never be committed — only the template (`.env.example`) is tracked. In
production, set these as your host's environment variables / secrets rather
than committing an `.env` file.

## Project Structure

```
phishing-sim-platform/
├── backend/      FastAPI app, models, migrations, Celery workers
├── frontend/     React + Vite single-page app
├── nginx/        Reverse-proxy gateway config
└── docker-compose.yml
```

## Ethical Use Disclaimer

This platform simulates phishing for defensive security-awareness training.
Misuse can be illegal and harmful. By using it you agree to the following:

- **Written authorization required** — obtain explicit, written permission
  before running any campaign against any recipient.
- **Legal review** — have the program reviewed by your legal/compliance team
  before launch.
- **Never target external parties** — only run simulations against members of
  your own organization who fall under the authorization.
- **Comply with the law and policy** — follow all applicable local laws,
  regulations, and company policies.

The author assumes no liability for misuse. You are solely responsible for how
you operate this software.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the list of notable changes.

## Author

**Arnendu Biswas** — arnendubiswas5@gmail.com

## License

Released under the [MIT License](LICENSE). Note the authorized-use notice above:
the simulated-phishing functionality is intended solely for security-awareness
testing within your own organization.
