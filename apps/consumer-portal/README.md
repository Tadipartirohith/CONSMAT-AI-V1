# consumer-portal

Retail **consumer** portal (roadmap Step 8) — a light, read-only React (Vite + Tailwind) app where a
consumer follows their construction project(s): overall progress, the 9-phase timeline, and which
materials have been delivered vs are awaiting stock.

## Pages
- **Home** — pick who you are (stands in for login until identity-service lands), then see your
  projects as cards with a progress bar and current phase.
- **Project** — a friendly timeline of the 9 phases with status, plus per-phase delivery status
  ("Materials delivered: …" / "Awaiting stock: …") derived from hub→site dispatches.

## Services
nginx path-proxies to site-service (same-origin, read-only):

| Path | Service |
|------|---------|
| `/site/*` | site-service `/api/v1` |

## Run
```bash
docker compose -f infra/docker-compose.yml up -d --build
# consumer-portal → http://localhost:8097
```
Local dev (site-service on 8003): `npm install && npm run dev`.

## Note
No auth yet (identity-service pending, Q12). The consumer selector is a temporary stand-in for login;
real per-consumer auth will replace it.
