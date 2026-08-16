# Consmat AI — V1 (Hub-and-Spoke)

> **Status:** 🟢 Steps 1–8 complete — 4 backend microservices + 3 React frontends, all running via
> `docker compose`. See [`docs/`](./docs) for the design and [`docs/DECISIONS.md`](./docs/DECISIONS.md)
> for decisions and the remaining deferred items (auth, payments, gateway).

Consmat AI V1 is a **hub-and-spoke construction-materials distribution platform**. It replaces the
earlier buyer-centric marketplace with a distribution network where a central **hub** procures, owns,
prices, and dispatches material, and **spokes** (geo-fenced field agents) manage retail consumers and
their construction sites.

## The model

```
suppliers / vendors  ──►  HUB  ──►  SPOKE  ──►  retail consumer (site)
     (upstream)        (owns stock,  (field       (construction
                        prices,      agent +      project, phased
                        procures)    architect +   demand)
                                     civil engr)
```

- Inventory flows **downstream**: supplier → hub → site.
- Demand flows **upstream**: site phase completion → hub replenishes the next phase, just-in-time.
- The **spoke is a person (role)**, not a warehouse — the coordination/relationship layer. Physical
  material ships from the hub to the site.

## Actors & roles

| Actor | Sits at | Core job |
|-------|---------|----------|
| Retail consumer | site | Has a construction project served through a spoke |
| Spokesperson | spoke | Owns a geofence, the consumer relationship, and consumer classification |
| Architect | under spoke | Produces the site plan → the bill of materials (BOM) |
| Civil engineer | under spoke | Executes on site and updates **phase status** (the JIT trigger) |
| Hub supervisor | hub | Ops execution: inventory, dispatch, procurement runs |
| Hub manager | hub | Oversight, approvals, pricing, vendor list |
| Vendor / supplier | upstream | Sells material to the hub (the hub is also a supplier) |

## Core capabilities

- **Hub inventory** — owns stock with full inbound/outbound tracking (everything in and out).
- **Procurement + Hub LLM** — given a BOM, analyzes **profitability**, suggests **alternatives**, and
  **price-scouts** vendors/manufacturers for cheaper procurement.
- **Vendor registry** — the hub keeps a list of vendors and their pricing, and can add new vendors.
- **Site & phase management** — architect plans, civil-engineer phase updates, and phase-driven
  just-in-time material dispatch so sites never stall.
- **Pricing & margin** — the hub sets the selling price.

## Repository structure

| Path | Purpose |
|------|---------|
| [`docs/`](./docs) | Design documentation (HLD, LLD, SLD, decisions) |
| [`gateway/`](./gateway) | API gateway — ✅ single nginx ingress fronting all services (`/api/<service>/`) |
| [`services/`](./services) | Backend microservices — ✅ identity · inventory · procurement · site · pricing · payment (FastAPI) |
| [`apps/hub-console/`](./apps/hub-console) | Hub operations console (supervisor + manager) — ✅ built (React/Vite, `:8095`) |
| [`apps/spoke-app/`](./apps/spoke-app) | Spoke app (spokesperson + architect + civil engineer) — ✅ built (React/Vite, `:8096`) |
| [`apps/consumer-portal/`](./apps/consumer-portal) | Retail consumer portal — ✅ built (React/Vite, `:8097`) |
| [`infra/`](./infra) | Deployment — ✅ `docker-compose.yml` (Postgres + 4 services + 3 apps) |

## Design documents

- [**HLD**](./docs/HLD.md) — High-Level Design: architecture, actors, flows, modules.
- [**LLD**](./docs/LLD.md) — Low-Level Design: domain & role model (first cut), phases, LLM procurement.
- [**SLD**](./docs/SLD.md) — System-Level Design: deployment landscape, persistence, integrations.
- [**DECISIONS**](./docs/DECISIONS.md) — decision log and open questions.

## Build roadmap (one step at a time)

1. ✅ **Domain & role model** — entities, roles, phases, relationships ([docs/LLD.md](./docs/LLD.md)).
2. ✅ **Hub inventory** — append-only ledger, stock levels, weighted-avg valuation, reservations ([services/inventory-service](./services/inventory-service)).
3. ✅ **Vendor registry + price lists** — vendors, add-vendor, pricing, cheapest-first market view ([services/procurement-service](./services/procurement-service)).
4. ✅ **Procurement + Hub LLM** — cheapest-source planning, profitability, LLM advice (pluggable, graceful fallback), orders that receive into inventory ([services/procurement-service](./services/procurement-service)).
5. ✅ **Site & phase management** — spokes/consumers/sites, architect plans → BOM, 9-phase progress, phase-driven JIT dispatch drawing down inventory ([services/site-service](./services/site-service)).
6. ✅ **Spoke ops** — geofence coverage + auto-assignment, consumer intake & classification, spokesperson territory dashboard ([services/site-service](./services/site-service)).
7. ✅ **Pricing & margin** — hub sets selling price via margin-rule precedence (per-material/per-tier/global); feeds procurement profitability ([services/pricing-service](./services/pricing-service)).
8. ✅ **Frontends** — hub-console (`:8095`) · spoke-app (`:8096`) · consumer-portal (`:8097`), all React/Vite/Tailwind served via nginx path-proxy.

**Steps 1–8 complete + auth + payments + Hub LLM + API gateway.** ✅ **identity-service + JWT auth**
(Q12) · ✅ **payment-service** (config-driven, mock default — D11) · ✅ **Hub LLM set to Gemini**
(`infra/.env`, add a key to go live — D12) · ✅ **API gateway** (single ingress — D13). All major and
cross-cutting pieces are in place; real payment-provider API calls remain as extension points.

## Running the stack

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

| Component | URL |
|-----------|-----|
| Hub console | http://localhost:8095 |
| Spoke app | http://localhost:8096 |
| Consumer portal | http://localhost:8097 |
| API gateway | http://localhost:8088 (single API ingress; try `/` and `/health`) |
| identity-service | http://localhost:8005/docs |
| payment-service | http://localhost:8006/docs |
| inventory-service | http://localhost:8001/docs |
| procurement-service | http://localhost:8002/docs |
| site-service | http://localhost:8003/docs |
| pricing-service | http://localhost:8004/docs |

One PostgreSQL instance (host port 5433) with a database per service. Each service self-migrates and
seeds on start. Frontend API traffic flows browser → app nginx → **gateway** → service (same-origin, no
CORS); external clients can call the gateway directly. Tear down with
`docker compose -f infra/docker-compose.yml down` (add `-v` to wipe data).

**Demo logins** (password `consmat123`): `manager@consmat.com` / `supervisor@consmat.com` (hub console) ·
`spoke@consmat.com` / `architect@consmat.com` / `civil@consmat.com` (spoke app) · `demo@consmat.com`
(consumer portal) · plus `admin@consmat.com` and `vendor@consmat.com`.

**Enable the Hub LLM (procurement intelligence):** `infra/.env` already selects Gemini. Paste a
[Google AI Studio](https://aistudio.google.com/apikey) key into the `AI_API_KEY=` line, then:
```bash
docker compose -f infra/docker-compose.yml up -d procurement-service
```
Verify with `GET /api/v1/procurement/llm-status` (→ `live: true`). Without a key it runs deterministic-only.

**Payments:** the gateway is config-driven — set the provider in
[`services/payment-service/config.yaml`](./services/payment-service/config.yaml). The default `mock`
gateway settles instantly; real providers read their keys from the env vars named in that file. The
consumer portal has a **Pay for my project** flow (prices the BOM at the consumer's tier, then pays),
and the hub console has a **Payments** page.
