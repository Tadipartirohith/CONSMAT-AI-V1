# procurement-service

Vendor registry + price lists for Consmat AI V1 (roadmap Step 3). The hub keeps a list of vendors and
their pricing and can add new vendors at any time (decision D1). This service also exposes a
**cheapest-first market view** per material, which the procurement engine and Hub LLM will rank in
Step 4.

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL (own database, per D10).

## Data model
- **vendors** — `id, name, city, phone, gstin, is_hub_self, active`. `is_hub_self=true` models the hub's
  own supply as a vendor so procurement can treat it uniformly.
- **vendor_prices** — one current price per (vendor, material): `price, min_qty`. `material_id` is an
  opaque reference to the catalog owned by inventory-service (Q11).

## API (`/api/v1`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/vendors` | Add a vendor (id auto-generated from name) |
| GET | `/vendors?active=` | List vendors |
| GET | `/vendors/{id}` | Vendor + price list |
| PATCH | `/vendors/{id}` | Update contact / reactivate |
| DELETE | `/vendors/{id}` | Soft-deactivate (keeps history) |
| PUT | `/vendors/{id}/prices` | Upsert a price for a material |
| DELETE | `/vendors/{id}/prices/{material_id}` | Remove a price |
| GET | `/prices/{material_id}` | Cheapest-first market view across active vendors |
| POST | `/procurement/plan` | Deterministic cheapest-source plan for a demand (no LLM) |
| POST | `/procurement/analyze` | Plan + profitability + **Hub LLM advice** (graceful fallback) |
| POST | `/procurement/orders` | Create a procurement order from lines |
| GET | `/procurement/orders` | List orders (`?status=`) |
| GET | `/procurement/orders/{id}` | Order detail |
| POST | `/procurement/orders/{id}/receive` | Receive → posts inbound to inventory-service (idempotent per line) |
| GET | `/procurement/llm-status` | Whether the Hub LLM is live or stub |

Interactive docs at `/docs`. Health at `/health`.

## Procurement + Hub LLM (Step 4)
- **Deterministic engine** (`procurement_engine.py`) picks the cheapest active vendor per material and
  computes costs; profitability is computed when selling prices are supplied. This is the backbone.
- **Hub LLM** (`llm.py`, pluggable provider) *advises* on top — margin notes, alternatives, risk flags,
  a recommendation — and **never sets a price**. Disabled (stub) or on any error it falls back to the
  deterministic result. Configure via `AI_PROVIDER`/`AI_API_KEY`/`AI_MODEL` (see `.env.example`).
- **Receive → inventory:** `POST /procurement/orders/{id}/receive` posts each line to
  inventory-service `/inventory/inbound`. Per-line `received` flags make it retry-safe (no double count).

## Run (via infra compose)
```bash
docker compose -f infra/docker-compose.yml up -d --build
# procurement-service → http://localhost:8002  (docs at /docs)
```
The entrypoint self-creates its database (D10), runs `alembic upgrade head`, seeds vendors, then serves.

## Test
```bash
pip install -r requirements.txt pytest
pytest
```
