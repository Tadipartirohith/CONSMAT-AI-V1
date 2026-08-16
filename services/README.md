# services

Backend microservices for Consmat AI V1 (per decision **D8**). Each service is independently
deployable, owns its own database (**database-per-service**, D10), and exposes a REST API. Services talk
to each other synchronously over REST to start; event-driven flows (e.g. phase triggers) come later.

## Target service map

| Service | Owns | Status | Roadmap step |
|---------|------|--------|--------------|
| **inventory-service** | Hub stock + append-only ledger (+ materials catalog) | 🟢 built | Step 2 |
| **procurement-service** | Vendors, price lists, procurement orders, procurement LLM | 🟢 built | Steps 3–4 |
| **site-service** | Spokes, consumers, sites, plans, BOM, phases, dispatch, spoke ops | 🟢 built | Steps 5–6 |
| **pricing-service** | Selling price + margin (rule precedence); feeds procurement profitability | 🟢 built | Step 7 |
| **identity-service** | Users, roles, JWT issuance; every service validates locally with the shared secret | 🟢 built | (cross-cutting) |
| **payment-service** | Config-driven payment gateway (mock default; providers + key env-names in config.yaml) | 🟢 built | (cross-cutting) |
| **gateway** (top-level [`../gateway`](../gateway)) | Single nginx ingress fronting all services under `/api/<service>/`; all frontend + external API traffic flows through it | 🟢 built | (cross-cutting) |

## Conventions

- **Stack:** FastAPI + SQLAlchemy 2.0 + Alembic on PostgreSQL (D9).
- **Layout:** each service has `app/` (FastAPI), `alembic/` (migrations), `Dockerfile`, `requirements.txt`, `tests/`.
- **Config:** via environment (`DATABASE_URL`, `API_PREFIX`, …); secrets in `.env` (gitignored).
- **Migrations:** `alembic upgrade head` on start (via the container entrypoint), then optional seed.
- **API prefix:** `/api/v1`.

See [`../docs/HLD.md`](../docs/HLD.md) and [`../docs/LLD.md`](../docs/LLD.md).
