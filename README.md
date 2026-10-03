# Phishing Simulation Platform

A full-stack phishing simulation and security awareness training platform for
**authorized** security-awareness programs and red-team exercises (the
GoPhish / KnowBe4 category of defensive tooling). It lets an organization run
controlled simulated-phishing campaigns against its own employees, deliver
training to anyone who interacts with a simulation, and report on results —
all scoped per tenant.

> **Authorized use only.** This software is intended solely for simulated
> phishing against users who have consented to security-awareness testing
> within your own organization. Do not use it to target anyone without explicit
> authorization.

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

**Backend:** FastAPI · async SQLAlchemy · PostgreSQL · Alembic · Celery · Redis
**Frontend:** React · TypeScript · Vite · Tailwind CSS · Recharts · React Router

## Getting Started

### Prerequisites

- Docker Desktop (for PostgreSQL, Redis, and the optional Mailpit mail catcher)
- Python 3.12 and Node.js 20 (for running backend/frontend outside Docker)

### Run everything with Docker

```bash
# from the project root
cp .env.example .env    # then edit the values
docker compose up -d --build
```

The app is served through the nginx gateway at **http://localhost:8080**.

### Run for local development

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
npm run dev        # http://localhost:5173

# 4. Celery worker (needed for campaign sending)
cd backend
celery -A app.workers.email_worker.celery_app worker --loglevel=info --pool=solo
```

### Configuration

Copy `.env.example` to `.env` and fill in the values. `.env` is gitignored and
must never be committed — only the template (`.env.example`) is tracked.

## Project Structure

```
phishing-sim-platform/
├── backend/      FastAPI app, models, migrations, Celery workers
├── frontend/     React + Vite single-page app
├── nginx/        Reverse-proxy gateway config
└── docker-compose.yml
```

## Author

**Arnendu Biswas** — arnendubiswas5@gmail.com

## License

This project is provided for authorized security-awareness training and
educational use. See the authorized-use notice above.
