# pricing-service

The hub's selling price + margins for Consmat AI V1 (roadmap Step 7). Decision D1: the hub sets the
price. Selling price = **current inventory landed cost × (1 + margin%)**, where the margin is resolved
from a flexible rule table.

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL (own database, per D10).

## Margin model (Q3)
One `margin_rules` table supports flat, per-tier, per-material, and per-(material,tier) margins at once.
For a given `(material, tier)` the applied margin is resolved by **precedence**:

1. `(material, tier)` — most specific
2. `(material, *)` — per-material default
3. `(*, tier)` — per-tier default
4. `(*, *)` — global default
5. service default (`DEFAULT_MARGIN_PCT`) if no rule exists

Landed cost comes from inventory-service (`avg_cost`), so prices track real procurement cost.

## API (`/api/v1`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/margins` | List margin rules |
| PUT | `/margins` | Upsert a rule `{material_id?, tier?, margin_pct}` |
| DELETE | `/margins/{id}` | Remove a rule |
| GET | `/price/{material_id}?tier=` | Unit selling price for a material at a tier |
| POST | `/quote` | Priced quote for `{tier, items:[{material_id, qty}]}` |
| GET | `/selling-prices?tier=` | `material_id → unit price` map (consumed by procurement `/analyze`) |

Interactive docs at `/docs`. Health at `/health`.

## Closes the loop
`GET /selling-prices?tier=` feeds procurement-service `/analyze`, so the hub's **profitability** numbers
(buy from cheapest vendor vs sell at hub price) are now real end-to-end. Seeded defaults: global 12%,
retail (individual) 18%, contractor 12%, commercial 9%, government 10%, and cement+individual 20%.

## Run (via infra compose)
```bash
docker compose -f infra/docker-compose.yml up -d --build
# pricing-service → http://localhost:8004  (docs at /docs)
```
