# Consmat AI V1 — Low-Level Design (LLD)

> **Status:** 🟢 As-built · **Version:** 1.0 · **API version:** `v1` (each service serves under `/api/v1`)

Detailed internal design of the running system: services, data models, the full API surface, auth,
domain algorithms, and cross-service calls. See [HLD.md](./HLD.md) for the big picture and
[SLD.md](./SLD.md) for deployment.

---

## Table of Contents
1. [Service architecture](#1-service-architecture)
2. [Data model](#2-data-model)
3. [Domain algorithms](#3-domain-algorithms)
4. [API reference](#4-api-reference)
5. [Authentication & roles](#5-authentication--roles)
6. [Hub LLM](#6-hub-llm)
7. [Cross-service calls](#7-cross-service-calls)
8. [Frontend internals](#8-frontend-internals)
9. [Configuration](#9-configuration)

---

## 1. Service Architecture

Six FastAPI services, each with **its own database**, an identical stack, and the same layout
(`app/` = FastAPI, `alembic/` = migrations, `Dockerfile`, `tests/`). Each service self-creates its DB,
runs migrations, and seeds on start.

| Service | Host port | Database | Purpose |
|---------|-----------|----------|---------|
| identity | 8005 | identity | Users, roles, JWT issuance |
| inventory | 8001 | inventory | Materials catalog, stock + ledger |
| procurement | 8002 | procurement | Vendors + prices, planning, LLM, orders |
| pricing | 8004 | pricing | Margin rules, selling price |
| site | 8003 | site | Spokes/consumers/sites, plans, phases, dispatch, backfill |
| payment | 8006 | payment | Config-driven gateway, payments |

Stack: **FastAPI 0.115 · SQLAlchemy 2.0 · Alembic · PostgreSQL · PyJWT** (+ bcrypt in identity, PyYAML in
payment). LLM/HTTP calls use the Python stdlib `urllib`.

---

## 2. Data Model

Database-per-service; `material_id`, `consumer_id`, `spoke_id`, `vendor_id` are **opaque cross-service
references** (no cross-DB foreign keys).

### 2.1 identity
- **users** — `id` (email, PK), `name`, `role`, `org_ref` (spoke/consumer/vendor id), `password_hash` (bcrypt), `active`.

### 2.2 inventory
```mermaid
erDiagram
    MATERIAL ||--o| INVENTORY_ITEM : "stocked as"
    MATERIAL ||--o{ LEDGER_ENTRY : records
    MATERIAL { string id PK; string name; string unit; string grade; float per_sqft }
    INVENTORY_ITEM { string material_id PK; num on_hand; num reserved; num avg_cost }
    LEDGER_ENTRY { int id PK; string material_id; string direction; num qty; num unit_cost; num balance_after; string ref_type; string ref_id; datetime at }
```
`direction ∈ {inbound, outbound, adjustment}`; `on_hand` is the running sum of ledger `qty`.

### 2.3 procurement
```mermaid
erDiagram
    VENDOR ||--o{ VENDOR_PRICE : "price list"
    PROCUREMENT_ORDER ||--|{ PROCUREMENT_LINE : contains
    VENDOR { string id PK; string name; string city; bool is_hub_self; bool active }
    VENDOR_PRICE { int id PK; string vendor_id; string material_id; num price; num min_qty }
    PROCUREMENT_ORDER { int id PK; string status; num total_cost; datetime received_at }
    PROCUREMENT_LINE { int id PK; int order_id; string material_id; string vendor_id; num qty; num unit_cost; bool received }
```
`ProcurementOrder.status ∈ {draft, approved, received, cancelled}`; `code = PO-{id}`.

### 2.4 pricing
- **margin_rules** — `id`, `material_id?` (NULL = any), `tier?` (NULL = any), `margin_pct`.

### 2.5 site
```mermaid
erDiagram
    SPOKE ||--o{ SPOKE_AREA : covers
    SPOKE ||--o{ CONSUMER : serves
    CONSUMER ||--o{ SITE : owns
    SITE ||--|{ BOM_LINE : has
    SITE ||--|{ PHASE_PROGRESS : "tracked by"
    SITE ||--o{ DISPATCH : receives
    DISPATCH ||--|{ DISPATCH_LINE : contains
    SPOKE { string id PK; string name; string geofence; bool active }
    SPOKE_AREA { int id PK; string spoke_id; string area }
    CONSUMER { string id PK; string name; string tier; string spoke_id }
    SITE { int id PK; string consumer_id; num area_sqft; int floors; string construction_type; string status; num total_area }
    BOM_LINE { int id PK; int site_id; string material_id; num total_qty }
    PHASE_PROGRESS { int id PK; int site_id; int phase_seq; string status; datetime completed_at }
    DISPATCH { int id PK; int site_id; int phase_seq; string status }
    DISPATCH_LINE { int id PK; int dispatch_id; string material_id; num qty; string status }
```
`consumer.tier ∈ {individual, contractor, commercial, government}`; `phase_progress.status ∈ {pending,
in_progress, done}`; `dispatch.status ∈ {dispatched, partial, pending}`; `dispatch_line.status ∈
{dispatched, short}`. Reference table **phases** (9 rows, `seq, name, repeats_per_floor`).

### 2.6 payment
- **payments** — `id`, `ref` (e.g. `SITE-1`), `consumer_id`, `amount`, `currency`, `provider`,
  `provider_ref`, `status ∈ {pending, paid, failed, refunded}`, `created_at`, `paid_at`; `code = PAY-{id}`.

---

## 3. Domain Algorithms

### 3.1 Inventory (inventory-service)
- **Weighted-average cost:** each inbound → `avg_cost = (on_hand·avg_cost + qty·unit_cost)/(on_hand+qty)`; outbound valued at `avg_cost`.
- **Reservations:** `available = on_hand − reserved`; `reserve` holds without a ledger move; `outbound(from_reservation)` converts it.
- **Guards:** oversell blocked (409); adjustments can't drive `on_hand` negative. Item row locked (`SELECT … FOR UPDATE`) during mutation.
- **Ledger:** every movement appends one entry with `balance_after`; `on_hand` is reconstructable.

### 3.2 Procurement (procurement-service)
- **Cheapest-source plan:** for each demand line, pick the cheapest **active** vendor from the market view; `line_cost = qty × price`; flag `below_min_qty`.
- **Profitability:** with selling prices, per line `margin = sell − buy`; totals + `loss_making` flags.

### 3.3 Pricing (pricing-service)
- **Margin precedence:** `(material,tier) > (material,*) > (*,tier) > (*,*) > service default`.
- **Selling price** = inventory `avg_cost` × (1 + margin%).

### 3.4 BOM & 9-phase (site-service, `bom.py`)
- **BOM total:** `qty = area_sqft × floors × per_sqft × type_mult` (economy 0.9 / standard 1.0 / premium 1.18); cement ceil, others round.
- **9 phases:** excavation & footing · foundation & plinth · RCC superstructure (repeats/floor) · masonry · roofing/slab · internal plastering · external plastering · flooring & tiling · MEP & finishing.
- **Phase slice:** each material's total distributed by a tunable weight matrix (sums to 1.0/material).

### 3.5 Dispatch & backfill (site-service)
- **Dispatch:** completing phase N computes phase N+1's slice and posts an `outbound` per material to inventory; a 409 marks that line `short` → dispatch `partial`/`pending` (the demand signal).
- **Backfill:** `backfill_site` / `backfill_all` retry every `short` line against current stock; on success the line → `dispatched` and the dispatch status is recomputed (heals `partial` → `dispatched`). Idempotent.

### 3.6 Geofence (site-service, `geofence.py`)
- A spoke covers area keywords; a location is served by the spoke whose keyword appears in it (most specific wins). Intake auto-assigns the spoke.

---

## 4. API Reference

All paths under `/api/v1`. Auth column: *any* = any authenticated user; otherwise the required role(s);
*none* = public. Reads are generally *any*; writes are role-scoped.

### 4.1 identity
| Method | Path | Auth |
|--------|------|------|
| POST | `/auth/login` | none |
| GET | `/auth/me` | any |
| GET / POST | `/users` | admin, hub_manager |

### 4.2 inventory
| Method | Path | Auth |
|--------|------|------|
| GET | `/materials` · `/inventory` · `/inventory/{m}` · `/inventory/{m}/ledger` · `/ledger` | any |
| POST | `/inventory/inbound` · `/outbound` · `/adjust` · `/reserve` · `/release` | service, hub_supervisor, hub_manager |

### 4.3 procurement
| Method | Path | Auth |
|--------|------|------|
| GET | `/vendors` · `/vendors/{id}` · `/prices/{m}` · `/procurement/orders` · `/procurement/llm-status` | any |
| POST | `/vendors` · PUT `/vendors/{id}/prices` · PATCH/DELETE `/vendors/{id}` · DELETE price | hub_supervisor, hub_manager |
| POST | `/procurement/plan` · `/procurement/analyze` | any |
| POST | `/procurement/orders` · `/procurement/orders/{id}/receive` | hub_supervisor, hub_manager |

### 4.4 pricing
| Method | Path | Auth |
|--------|------|------|
| GET | `/margins` · `/price/{m}?tier=` · `/selling-prices?tier=` · POST `/quote` | any |
| PUT | `/margins` · DELETE `/margins/{id}` | hub_manager |

### 4.5 site
| Method | Path | Auth |
|--------|------|------|
| GET | `/phases` · `/spokes` · `/spokes/{id}` · `/spokes/{id}/sites` · `/spokes/{id}/dashboard` · `/consumers` · `/sites` · `/sites/{id}` | any |
| POST | `/spokes` · `/spokes/{id}/areas` · `/consumers` · PATCH `/consumers/{id}` · `/intake` · `/sites` · `/sites/{id}/plan` · `/sites/{id}/start` · `/sites/{id}/phases/{seq}/complete` | spokesperson, architect, civil_engineer |
| POST | `/sites/{id}/backfill` · `/backfill` | field roles + hub_supervisor, hub_manager |

### 4.6 payment
| Method | Path | Auth |
|--------|------|------|
| GET | `/payments/config` · `/payments` · `/payments/{id}` | any |
| POST | `/payments` · `/payments/{id}/confirm` | consumer, hub_manager, hub_supervisor, spokesperson |

*(admin bypasses all role checks.)*

---

## 5. Authentication & Roles

- **Issuance (identity):** `POST /auth/login` verifies bcrypt, returns a JWT — `{sub, role, name, org_ref, iat, exp}` (HS256, 24h).
- **Validation (every service):** an identical `app/auth.py` decodes the token with the shared
  `JWT_SECRET`; `current_user` (401 if missing/invalid), `require_role(*roles)` (403; admin bypass).
- **Service tokens:** `service_token()` mints a short-lived `{role: service}` JWT for internal calls.
- **Roles:** `admin, hub_manager, hub_supervisor, spokesperson, architect, civil_engineer, consumer,
  vendor` (+ `service`).

| Area | Read | Write |
|------|------|-------|
| inventory | any | service / hub staff |
| procurement (vendors, orders) | any | hub staff |
| pricing (margins) | any | hub_manager |
| site (field actions) | any | spoke team |
| site (backfill) | any | spoke team + hub staff |
| payment (create) | any | consumer / hub / spokesperson |

Demo users (password `consmat123`): `admin@`, `manager@`, `supervisor@`, `spoke@`, `architect@`,
`civil@`, `demo@` (consumer), `vendor@` — all `@consmat.com`.

---

## 6. Hub LLM

- **Where:** procurement-service `app/llm.py`; endpoint `POST /procurement/analyze`, status `/procurement/llm-status`.
- **Provider:** pluggable (`AI_PROVIDER` = stub | gemini | openai | groq | openrouter | openai-compat | anthropic); **live on `gemini` / `gemini-flash-lite-latest`**. Transport = stdlib `urllib`, `response_format=json_object`, temp 0.
- **Input:** demand, deterministic plan, profitability, and the full market prices per material.
- **Output (advice only):** `summary`, `profitability_note`, `alternatives[]`, `flags[]`, `recommendation`.
- **Determinism boundary:** the LLM never computes money; on any error/quota it returns `None` and
  `/analyze` reports `engine: deterministic`. Selling prices for profitability are fetched from
  pricing-service when a `tier` is given.

---

## 7. Cross-Service Calls

Internal calls go **directly** by service name (not via the gateway), each carrying a `service` token:

| Caller | Callee | For |
|--------|--------|-----|
| procurement | inventory | `POST /inventory/inbound` (receive an order) |
| procurement | pricing | `GET /selling-prices?tier=` (profitability) |
| site | inventory | `GET /materials` (BOM coefficients), `POST /inventory/outbound` (dispatch) |
| pricing | inventory | `GET /inventory/{m}` (landed `avg_cost`) |

Configured via `INVENTORY_URL` / `PRICING_URL` env (e.g. `http://inventory-service:8000`).

---

## 8. Frontend Internals

React 18 + Vite + Tailwind; each app: `src/api.js` (fetch wrapper attaching the JWT, 401 → logout),
`src/auth.js` (login/token), a `Login` page, and role display. API paths (`/inv`, `/proc`, `/price`,
`/pay`, `/site`, `/id`) are proxied by the app's nginx **to the gateway**.

| App | Notable pages / actions |
|-----|-------------------------|
| hub-console | Overview (stock, margins, **network re-dispatch**), Inventory (inbound/ledger), Vendors (registry/prices/market), Procurement (plan/analyze **+ LLM advice**/order/receive), Pricing (rules/lookup), Payments |
| spoke-app | Territory (dashboard), Intake (classify + geofence), Sites, Site detail (plan/start/complete phase **/ backfill**) |
| consumer-portal | Projects, phase timeline + delivery status, **Pay for project** (price BOM at tier → pay) |

---

## 9. Configuration

- **Catalog & BOM** — materials + `per_sqft` seeded in inventory; 9 phases + weight matrix in site (`bom.py`); construction-type multipliers in code.
- **Pricing** — margin rules seeded (global 12%, per-tier 18/12/9/10, cement+individual 20%).
- **Payments** — provider + API bases + secret **env-var names** in `payment-service/config.yaml`; secrets in env.
- **AI + secrets** — `infra/.env` (gitignored): `JWT_SECRET`, `AI_PROVIDER/AI_API_KEY/AI_MODEL`, gateway/provider secrets.
- **Ports & URLs** — see [SLD.md](./SLD.md).

---

*Related: [HLD.md](./HLD.md) · [SLD.md](./SLD.md) · [DECISIONS.md](./DECISIONS.md)*
