# hub-console

Hub operations console (roadmap Step 8) for **manager + supervisor** roles. A React (Vite + Tailwind)
SPA covering the hub side of the platform: inventory, vendors, procurement (+ Hub LLM), and pricing.

## Pages
- **Overview** — stock value, vendor/order counts, Hub LLM status, inventory + margin snapshots.
- **Inventory** — stock positions, receive inbound, per-material ledger drill-down.
- **Vendors** — registry, add vendor, set prices, cheapest-first market view.
- **Procurement** — build a demand → cheapest-source plan + profitability (real hub prices) + Hub LLM
  advice → create order → receive into inventory.
- **Pricing** — margin rules (precedence), set rule, price lookup by tier.

## How it talks to the services
Since the API gateway is deferred, the console's **nginx path-proxies** to each service, keeping the
browser same-origin (no CORS):

| Path | Service |
|------|---------|
| `/inv/*` | inventory-service `/api/v1` |
| `/proc/*` | procurement-service `/api/v1` |
| `/price/*` | pricing-service `/api/v1` |
| `/site/*` | site-service `/api/v1` |

`vite.config.js` mirrors the same proxy for `npm run dev` against the compose host ports.

## Run
Via the infra compose (built + served by nginx):
```bash
docker compose -f infra/docker-compose.yml up -d --build
# hub-console → http://localhost:8090
```

Local dev (services must be up on 8001–8004):
```bash
npm install && npm run dev
```

## Note
No auth yet (identity-service is pending, Q12) — the console calls the services directly through the
proxy. Login/roles will be layered in when identity-service lands.
