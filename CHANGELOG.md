# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-tenant data model — every record is scoped by `tenant_id`.
- Authentication with JWT access and refresh tokens, plus role-based access.
- Campaign management: build campaigns from a template, a landing page, an
  SMTP profile, and a selected set of targets, then launch them.
- Email templates and landing pages with full CRUD and a live preview rendered
  against sample target data.
- Target and target-group management, including CSV import.
- Tracking of opens, clicks, and credential-submission events.
- Shortened tracking links (`/s/{code}`) that redirect to the full tracked URL.
- Training modules with quizzes, assignable to targets, plus a public training
  page for recipients who interact with a simulation.
- Reporting: per-campaign dashboards, timelines, and department breakdowns.
- Audit logging middleware and Redis-backed rate limiting on public endpoints.
- Scheduled purge of expired data via a Celery beat task.
- SMTP profiles with passwords encrypted at rest.
- React + TypeScript single-page frontend with a dark interface theme.

### Changed
- Configuration normalizes managed `postgres://` database URLs to the async
  driver, so the app runs on managed Postgres without manual rewriting.
- Celery broker and result backend default to `REDIS_URL` when not set
  explicitly.
- The frontend API base URL is configurable via `VITE_API_BASE_URL` for
  split-service deployments; it falls back to the dev proxy path otherwise.
- The default admin account can be seeded from `ADMIN_EMAIL` and
  `ADMIN_PASSWORD` environment variables.

### Security
- Simulated-phishing functionality is intended strictly for authorized
  security-awareness testing within your own organization.
