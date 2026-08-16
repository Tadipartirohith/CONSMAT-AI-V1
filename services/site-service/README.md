# site-service

The field domain for Consmat AI V1 (roadmap Step 5): spokes, consumers, sites, architect plans → BOM,
the 9-phase progress model, and **phase-driven just-in-time dispatch** from hub inventory (D3/D4).

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL (own database, per D10).

## Data model
- **spokes** — geo-fenced spokesperson (Step 6 adds richer geofence/classification logic).
- **consumers** — `tier ∈ {individual, contractor, commercial, government}` (D5), attached to a spoke.
- **sites** — a consumer's construction project (`area_sqft`, `floors`, `construction_type`).
- **phases** — reference table of the 9 phases (seeded).
- **bom_lines** — per-material total quantity for a site (from the architect plan).
- **phase_progress** — per-site phase status (`pending`/`in_progress`/`done`).
- **dispatches / dispatch_lines** — hub → site shipments per phase.

## Key flow (the demand loop)
1. **Architect** — `POST /sites/{id}/plan`: fetches `per_sqft` coefficients from inventory-service,
   computes the BOM totals, and lays out the 9 phases.
2. **Start** — `POST /sites/{id}/start`: phase 1 → in-progress and dispatches its material slice.
3. **Civil engineer** — `POST /sites/{id}/phases/{seq}/complete`: marks a phase done and **triggers
   dispatch of the next phase** (JIT). Each dispatch pulls stock from inventory-service (`/inventory/outbound`).
   If stock is short, the dispatch line is marked `short` (the signal for the hub to procure).

## API (`/api/v1`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/phases` | The 9 reference phases |
| POST/GET | `/spokes` | Create / list spokes |
| POST/GET | `/consumers` | Create / list consumers |
| POST/GET | `/sites` | Create / list sites |
| GET | `/sites/{id}` | Site detail (BOM, phases, dispatches) |
| POST | `/sites/{id}/plan` | Architect: generate BOM + phases |
| POST | `/sites/{id}/start` | Begin: dispatch phase 1 |
| POST | `/sites/{id}/phases/{seq}/complete` | Civil engineer: complete phase → JIT dispatch next |
| POST | `/sites/{id}/backfill` | Retry this site's still-short dispatch lines against current stock |
| POST | `/backfill` | Network-wide backfill across all sites (hub action after a replenishment) |
| GET | `/spokes/{id}` | Spoke detail + coverage areas |
| POST | `/spokes/{id}/areas` | Add a geofence coverage keyword |
| GET | `/spokes/{id}/sites` | Territory sites (via the spoke's consumers) |
| GET | `/spokes/{id}/dashboard` | Territory summary: consumers by tier, sites by status, shortfalls needing attention |
| POST | `/intake` | Consumer intake → classify + auto-assign spoke by geofence |
| PATCH | `/consumers/{id}` | Reclassify tier / update phone |

Interactive docs at `/docs`. Health at `/health`.

## Spoke ops (Step 6)
- **Geofence (Q7):** each spoke covers area keywords; a location is served by the spoke whose covered
  keyword appears in it (most specific wins). `POST /spokes/{id}/areas` manages coverage.
- **Intake:** `POST /intake {name, tier, location}` classifies the consumer and **auto-assigns** the
  serving spoke by geofence (fails if no spoke covers the location).
- **Territory view:** `/spokes/{id}/dashboard` gives the spokesperson their consumers (by tier), sites
  (by status), and any dispatches with material shortfalls to chase.

## Run (via infra compose)
```bash
docker compose -f infra/docker-compose.yml up -d --build
# site-service → http://localhost:8003  (docs at /docs)
```

## Notes
- The phase→material weight matrix (`bom.py`) is a tunable default (Q2). Per-floor RCC repetition is
  marked in the phase reference but modelled at building level for now (refinement tracked in Q2).
