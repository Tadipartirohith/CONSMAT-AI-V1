# consumer-portal

Retail **consumer** portal (roadmap Step 8) — a light, read-only React (Vite + Tailwind) app where a
consumer follows their construction project(s): overall progress, the 9-phase timeline, and which
materials have been delivered vs are awaiting stock.

## Pages
- **Home** — the logged-in consumer's projects as cards with a progress bar and current phase.
- **Project** — a friendly timeline of the 9 phases with per-phase delivery status ("Materials
  delivered: …" / "Awaiting stock: …"), plus a **Project payment** panel: it prices the project's BOM
  at the consumer's tier (pricing-service) and lets them **Pay** (payment-service).

## Services
nginx path-proxies (same-origin):

| Path | Service |
|------|---------|
| `/id/*` | identity-service (login) |
| `/site/*` | site-service (projects) |
| `/price/*` | pricing-service (project estimate) |
| `/pay/*` | payment-service (pay flow) |

## Run
```bash
docker compose -f infra/docker-compose.yml up -d --build
# consumer-portal → http://localhost:8097
```
Local dev (site-service on 8003): `npm install && npm run dev`.

## Note
No auth yet (identity-service pending, Q12). The consumer selector is a temporary stand-in for login;
real per-consumer auth will replace it.
