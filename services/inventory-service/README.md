# inventory-service

Hub stock + **append-only ledger** for Consmat AI V1 (roadmap Step 2). The hub is the sole inventory
location (decision D3); every movement is recorded immutably and `on_hand`/`avg_cost` are maintained
transactionally.

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL (per D8/D9/D10).

## Data model
- **materials** — reference catalog (provisionally owned here; see Q11).
- **inventory_items** — `on_hand`, `reserved`, `avg_cost` per material.
- **ledger_entries** — immutable movements (`inbound` / `outbound` / `adjustment`) with `balance_after`.

## API (`/api/v1`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/inventory` | List stock positions |
| GET | `/inventory/{material_id}` | One material's position |
| GET | `/inventory/{material_id}/ledger` | Movement history for a material |
| GET | `/ledger` | Recent movements (all materials) |
| POST | `/inventory/inbound` | Receive stock (procurement / own supply); updates weighted-avg cost |
| POST | `/inventory/outbound` | Dispatch to a site; guarded against oversell |
| POST | `/inventory/adjust` | Signed correction (stock count / wastage) |
| POST | `/inventory/reserve` | Hold available stock for an upcoming dispatch |
| POST | `/inventory/release` | Release a reservation |

Interactive docs at `/docs`. Health at `/health`.

## Run (via infra compose)
```bash
docker compose -f infra/docker-compose.yml up -d --build
# inventory-service → http://localhost:8001  (docs at /docs)
```
The container entrypoint runs `alembic upgrade head`, seeds the base materials, then serves.

## Test
```bash
pip install -r requirements.txt pytest
pytest            # ledger logic tests (in-memory SQLite harness)
```

## Design semantics
- **Weighted-average costing:** each inbound recomputes `avg_cost`; outbound is valued at `avg_cost`.
- **Reservations:** `available = on_hand - reserved`; `reserve` holds stock without a ledger movement;
  `outbound(from_reservation=True)` converts a reservation into an actual outbound.
- **Concurrency:** item rows are locked (`SELECT ... FOR UPDATE`) during mutation to prevent oversell.
- **Auditability:** `on_hand` equals the running sum of ledger `qty`; `balance_after` snapshots it per entry.
