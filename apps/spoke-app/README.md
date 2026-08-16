# spoke-app

Field app (roadmap Step 8) for the **spokesperson, architect, and civil engineer**. A React (Vite +
Tailwind) SPA over site-service that drives the demand loop.

## Pages
- **Territory** — pick a spoke → dashboard (consumers by tier, sites by status, coverage) and the sites
  in that territory, with deliveries needing attention (material shortfalls).
- **Intake** — classify a consumer (tier) and **auto-assign the serving spoke by location** (geofence);
  manage spoke coverage areas.
- **Sites** — list and create construction sites.
- **Site detail** — the workflow hub:
  - **Architect:** Generate plan → BOM.
  - **Start construction:** dispatch phase 1.
  - **Civil engineer:** Complete the in-progress phase → triggers JIT dispatch of the next phase.
  - Live view of the 9-phase tracker and hub→site dispatches (with `short` lines flagged).

## Services
nginx path-proxies keep the browser same-origin:

| Path | Service |
|------|---------|
| `/site/*` | site-service `/api/v1` |
| `/inv/*` | inventory-service `/api/v1` (context) |

## Run
```bash
docker compose -f infra/docker-compose.yml up -d --build
# spoke-app → http://localhost:8096
```
Local dev (site-service on 8003): `npm install && npm run dev`.

## Note
No auth yet (identity-service pending, Q12); roles (spokesperson/architect/civil engineer) are actions
in one app for now and will be split by login later.
