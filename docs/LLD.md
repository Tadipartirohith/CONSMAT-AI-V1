# Consmat AI V1 — Low-Level Design (LLD)

> **Status:** 🟢 As-built · **Version:** 1.1 · **API version:** `v1` (each service serves under `/api/v1`)

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
    MATERIAL ||--o| INVENTORY_ITEM : "material rollup"
    MATERIAL ||--o{ PRODUCT : "branded as"
    PRODUCT ||--o| PRODUCT_STOCK : "stocked as"
    MATERIAL ||--o{ LEDGER_ENTRY : records
    MATERIAL { string id PK; string name; string unit; string grade; float per_sqft }
    PRODUCT { string id PK; string material_id; string brand; string name; string grade; bool active }
    INVENTORY_ITEM { string material_id PK; num on_hand; num reserved; num avg_cost }
    PRODUCT_STOCK { string product_id PK; string material_id; num on_hand; num reserved; num avg_cost }
    LEDGER_ENTRY { int id PK; string material_id; string product_id; string direction; num qty; num unit_cost; num balance_after; string ref_type; string ref_id; datetime at }
```
`direction ∈ {inbound, outbound, adjustment}`. **`PRODUCT_STOCK` is the source of truth per brand** (D18);
every product movement also updates the material `INVENTORY_ITEM` rollup so material-level views still
work. `available = on_hand − reserved` on both. Ledger entries carry the `product_id` when brand-level.

### 2.3 procurement
```mermaid
erDiagram
    VENDOR ||--o{ VENDOR_PRICE : "price list"
    PROCUREMENT_ORDER ||--|{ PROCUREMENT_LINE : contains
    VENDOR { string id PK; string name; string city; bool is_hub_self; bool active }
    VENDOR_PRICE { int id PK; string vendor_id; string product_id; string material_id; string brand; num price; num min_qty }
    PROCUREMENT_ORDER { int id PK; string status; num total_cost; datetime received_at }
    PROCUREMENT_LINE { int id PK; int order_id; string material_id; string product_id; string vendor_id; num qty; num unit_cost; bool received }
    VENDOR_REQUEST { int id PK; string action; string vendor_id; string name; string status; string requested_by; string decided_by }
    EXTERNAL_OFFER { int id PK; string material_id; string seller; num price; string source; string confidence }
```
`ProcurementOrder.status ∈ {draft, approved, received, cancelled}`; `code = PO-{id}`. Vendor pricing +
procurement lines are **product-level** (D14). **`VENDOR_REQUEST`** (D21): `action ∈ {add, remove}`,
`status ∈ {pending, approved, rejected}` — an operator requests, a supervisor/manager decides.
`EXTERNAL_OFFER` = advisory scouted prices (D16/D17), `confidence ∈ {indicative, firm}`.

### 2.4 pricing
- **margin_rules** — `id`, `product_id?` (NULL = any brand), `material_id?` (NULL = any), `tier?`
  (NULL = any), `margin_pct`. A product rule overrides its material rule (D22).

### 2.5 site
```mermaid
erDiagram
    SPOKE ||--o{ SPOKE_AREA : covers
    SPOKE ||--o{ CONSUMER : serves
    CONSUMER ||--o{ SITE : owns
    SITE ||--|{ BOM_LINE : has
    SITE ||--|{ PHASE_PROGRESS : "tracked by"
    SITE ||--o{ DISPATCH : receives
    SITE ||--o{ PHASE_DATE_CHANGE : "date approvals"
    SITE ||--o{ NOTIFICATION : "alerts"
    DISPATCH ||--|{ DISPATCH_LINE : contains
    CONSUMER { string id PK; string name; string tier; string spoke_id }
    SITE { int id PK; string consumer_id; num area_sqft; int floors; string construction_type; string status; num total_area }
    BOM_LINE { int id PK; int site_id; string material_id; string product_id; string product_name; num total_qty }
    PHASE_PROGRESS { int id PK; int site_id; int phase_seq; string status; date planned_start; date planned_end; bool dispatched; datetime completed_at }
    PHASE_DATE_CHANGE { int id PK; int site_id; int phase_seq; date old_end; date new_end; string status; string requested_by; string decided_by }
    NOTIFICATION { int id PK; int site_id; string spoke_id; string audience; int phase_seq; string kind; string message; bool read }
    DISPATCH { int id PK; int site_id; int phase_seq; string status }
    DISPATCH_LINE { int id PK; int dispatch_id; string material_id; string product_id; string product_name; num qty; string status }
```
`consumer.tier ∈ {individual, contractor, commercial, government}`; `phase_progress.status ∈ {pending,
in_progress, done}` with `planned_start/planned_end` dates + a `dispatched` idempotency flag;
`phase_date_change.status ∈ {pending, approved, rejected}` (D19); `notification.kind ∈ {dispatch_pending,
dispatched, low_stock}` (D20); `dispatch.status ∈ {dispatched, partial, pending}`; `dispatch_line.status
∈ {dispatched, short}`. BOM + dispatch lines are **product-level** (D18/D19). Reference table **phases**
(9 rows, `seq, name, repeats_per_floor`). *(SPOKE/SPOKE_AREA unchanged from §2.5 v1.0.)*

### 2.6 payment
- **payments** — `id`, `ref` (e.g. `SITE-1`), `consumer_id`, `amount`, `released_amount`, `currency`,
  `provider`, `provider_ref`, `status ∈ {pending, paid, failed, refunded, held, released}`, `created_at`,
  `paid_at`, `released_at`; `code = PAY-{id}`. **Escrow:** a project payment is captured but `held`, and
  released in fractions (`released_amount` rises to `amount` → `released`) as deliveries are confirmed.

---

## 3. Domain Algorithms

### 3.1 Inventory (inventory-service)
- **Weighted-average cost:** each inbound → `avg_cost = (on_hand·avg_cost + qty·unit_cost)/(on_hand+qty)`; outbound valued at `avg_cost`. Maintained on both `ProductStock` and the material rollup.
- **Product-level stock (D18):** `receive_product` / `dispatch_product` / `reserve_product` / `release_product` mutate the brand's `ProductStock` **and** the material `InventoryItem` rollup in one transaction, writing one ledger entry (with `product_id`).
- **3× buffer:** `low_stock_products` returns any product with `on_hand < 3 × reserved` (`status = low_stock`, or `no_stock` when `on_hand < reserved`). `reserve_product(allow_over=True)` lets committed demand exceed on-hand so the buffer flags early instead of blocking.
- **Guards:** oversell blocked (409); adjustments can't drive `on_hand` negative. Stock rows locked (`SELECT … FOR UPDATE`) during mutation.

### 3.2 Procurement (procurement-service)
- **Cheapest-source plan:** per demand line pick the cheapest **active** vendor offer (product-level); `line_cost = qty × price`; flag `below_min_qty`. Unavailable items are reported structurally (no vendor), never as a failure.
- **Web scout (D16/D17):** `/analyze` auto-scouts external prices (Tavily live search / Gemini grounding / estimate / stub) so the LLM can flag a cheaper source even when the registry already supplies it.
- **Vendor requests (D21):** `create_vendor_request` (operator) → `decide_vendor_request` (supervisor/manager) creates or deactivates the vendor.

### 3.3 Pricing (pricing-service)
- **Margin precedence (D22):** `(product,tier) > (product,*) > (material,tier) > (material,*) > (*,tier) > (*,*) > service default`.
- **Selling price** = landed cost × (1 + margin%); `price_product` uses the **brand's** `ProductStock.avg_cost`.

### 3.4 BOM & 9-phase (site-service, `bom.py`)
- **Product BOM (D19):** the CE/spoke enters product lines with whole-project totals (`set_bom`, editable before start); the hub reserves the committed demand per product; the auto-plan (material `per_sqft` × area × type_mult) remains as a legacy path.
- **9 phases:** excavation & footing · foundation & plinth · RCC superstructure (repeats/floor) · masonry · roofing/slab · internal plastering · external plastering · flooring & tiling · MEP & finishing.
- **Product phase slice:** each product's total is distributed across phases by **its material's** weight matrix (sums to 1.0/material); the sum of phase slices is what gets reserved so dispatch consumes it exactly.

### 3.5 Dispatch, scheduler & backfill (site-service)
- **Dispatch:** a phase's product slice posts a `product-outbound` (from the reservation) per line; a 409 marks that line `short` → dispatch `partial`/`pending` (the demand signal). `_ensure_phase_dispatched` uses the `dispatched` flag so a phase never double-dispatches.
- **JIT scheduler (D20):** a background thread (`run_scheduler_tick`, interval `SCHEDULER_INTERVAL_SECONDS`) scans active sites: ~3 days before the current phase's `planned_end` it writes a `dispatch_pending` notification, then (~1 day later) pre-dispatches the next phase and writes a `dispatched` notification. Idempotent; also runnable via `POST /scheduler/tick`.
- **Phase-date approval (D19):** `set_phase_dates` applies start (and the first end) directly; a later end-date change by a civil engineer creates a pending `PhaseDateChange`; `decide_phase_change` (spoke/manager) applies or rejects it.
- **Backfill:** `backfill_site` / `backfill_all` retry every `short` line (product-level) against current stock; on success the line → `dispatched` and the dispatch status heals. Idempotent.

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
| GET | `/users` · `/roles` | admin, hub_manager, hub_supervisor (Team portal) |
| POST | `/users` | actor must out-rank the new role (`service` for consumer/vendor provisioning) |
| PATCH | `/users/{email}` | actor must out-rank the user's current **and** new role (assign role / move to a spoke team via `org_ref` / (de)activate) |

### 4.2 inventory
| Method | Path | Auth |
|--------|------|------|
| GET | `/materials` · `/products` · `/products/search?q=` · `/products/{id}` · `/inventory` · `/inventory/{m}` · `/inventory/{m}/ledger` · `/ledger` | any |
| GET | `/product-stock` · `/product-stock/low` · `/product-stock/{id}` | any |
| POST | `/products` | service, hub_supervisor, hub_manager |
| POST | `/inventory/inbound` · `/outbound` · `/adjust` · `/reserve` · `/release` | service, hub_supervisor, hub_manager |
| POST | `/inventory/product-inbound` · `/product-outbound` · `/product-reserve` · `/product-release` | service, hub_supervisor, hub_manager |

### 4.3 procurement
| Method | Path | Auth |
|--------|------|------|
| GET | `/vendors` · `/vendors/{id}` · `/vendor-requests` · `/prices/{m}` · `/external-offers` · `/procurement/orders` · `/procurement/llm-status` | any |
| POST | `/vendors` · PUT `/vendors/{id}/prices` · PATCH/DELETE `/vendors/{id}` · DELETE price | hub_supervisor, hub_manager |
| POST | `/vendor-requests` | hub_ops, hub_supervisor, hub_manager |
| POST | `/vendor-requests/{id}/decide` | hub_supervisor, hub_manager *(enforced in service)* |
| POST | `/procurement/plan` · `/procurement/analyze` · `/procurement/scout` · `/external-offers/import` | any / hub staff |
| POST | `/procurement/orders` · `/procurement/orders/{id}/receive` | hub_supervisor, hub_manager |

### 4.4 pricing
| Method | Path | Auth |
|--------|------|------|
| GET | `/margins` · `/price/{m}?tier=` · `/price-product/{id}?tier=` · `/selling-prices?tier=` · POST `/quote` | any |
| PUT | `/margins` (product/material/tier) · DELETE `/margins/{id}` | hub_manager |

### 4.5 site
| Method | Path | Auth |
|--------|------|------|
| GET | `/phases` · `/spokes` · `/spokes/{id}` · `/spokes/{id}/sites` · `/spokes/{id}/dashboard` · `/consumers` · `/sites` · `/sites/{id}` · `/phase-changes` · `/notifications` | any |
| POST | `/spokes` · `/spokes/{id}/areas` · `/consumers` · PATCH `/consumers/{id}` · `/intake` · `/sites` · `/sites/{id}/plan` · `/sites/{id}/bom` · `/sites/{id}/start` · `/sites/{id}/phases/{seq}/complete` | spokesperson, architect, civil_engineer |
| POST | `/sites/{id}/phases/{seq}/dates` | field roles + hub_supervisor, hub_manager |
| POST | `/phase-changes/{id}/decide` | spoke / hub_supervisor / hub_manager *(enforced in service)* |
| POST | `/notifications/{id}/read` · `/scheduler/tick` · `/sites/{id}/backfill` · `/backfill` | any / field + hub staff |

### 4.6 payment
| Method | Path | Auth |
|--------|------|------|
| GET | `/payments/config` · `/payments` · `/payments/{id}` | any |
| POST | `/payments` (escrow by default) · `/payments/{id}/confirm` | consumer, hub_manager, hub_supervisor, spokesperson |
| POST | `/payments/release` (release held escrow by fraction) | `service` (site-service on delivery confirm) + hub/field |

*(admin bypasses all role checks.)*

---

## 5. Authentication & Roles

- **Issuance (identity):** `POST /auth/login` verifies bcrypt, returns a JWT — `{sub, role, name, org_ref, iat, exp}` (HS256, 24h).
- **Validation (every service):** an identical `app/auth.py` decodes the token with the shared
  `JWT_SECRET`; `current_user` (401 if missing/invalid), `require_role(*roles)` (403; admin bypass).
- **Service tokens:** `service_token()` mints a short-lived `{role: service}` JWT for internal calls.
- **Roles:** `admin, hub_manager, hub_supervisor, hub_ops, spokesperson, architect, civil_engineer,
  consumer, vendor` (+ `service`). `hub_ops` (D21) is an operator that can request vendor changes but
  not approve them.

| Area | Read | Write |
|------|------|-------|
| inventory | any | service / hub staff |
| procurement (vendors, orders) | any | hub staff |
| pricing (margins) | any | hub_manager |
| site (field actions) | any | spoke team |
| site (backfill) | any | spoke team + hub staff |
| payment (create) | any | consumer / hub / spokesperson |

Demo users (password `consmat123`): `admin@`, `manager@`, `supervisor@`, `ops@`, `spoke@`, `architect@`,
`civil@`, `demo@` (consumer), `vendor@` — all `@consmat.com`.

**Approval gates:** vendor add/remove — requested by `hub_ops`, decided by `hub_supervisor`/`hub_manager`
(D21). Phase end-date change — a `civil_engineer` edit becomes pending, approved by `spokesperson`/
`hub_supervisor`/`hub_manager` (D19); a spoke/manager edit applies directly.

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
| procurement | inventory | `POST /inventory/product-inbound` (receive a product line; falls back to `/inbound` for legacy material lines) |
| procurement | inventory | `GET /products/{id}` (denormalize brand/material on set-price) |
| procurement | pricing | `GET /selling-prices` (list-price profitability) |
| site | inventory | `GET /materials` (BOM coefficients); `POST /inventory/product-reserve` (commit BOM demand), `/product-outbound` (dispatch), `/product-release` (edit BOM) |
| pricing | inventory | `GET /product-stock/{id}` + `/products/{id}` (brand landed `avg_cost` + material), `GET /inventory/{m}` (material landed cost) |

Configured via `INVENTORY_URL` / `PRICING_URL` env (e.g. `http://inventory-service:8000`).

---

## 8. Frontend Internals

React 18 + Vite + Tailwind; each app: `src/api.js` (fetch wrapper attaching the JWT, 401 → logout),
`src/auth.js` (login/token), a `Login` page, and role display. API paths (`/inv`, `/proc`, `/price`,
`/pay`, `/site`, `/id`) are proxied by the app's nginx **to the gateway**.

| App | Notable pages / actions |
|-----|-------------------------|
| hub-console | Overview (**project-health donut** + **stock-buffer widget** + **Network-events feed** + awaiting-materials/re-dispatch); **Projects** (area cards + **URL-driven cross-area filters**, phase-date & coverage approval queues, project-name links); Inventory (**per-brand stock grouped by category, available clamped ≥ 0 + over-committed flag, product inbound, Procure per product = vendor + open-market rates → PO**, ledger); Vendors (registry/prices/market, role-aware request → approve add/remove, web scout); Procurement (plan/analyze + LLM advice + auto web scout/order/receive); Pricing (per-product + material/tier rules); Payments; **Team & access** (RBAC: add spokes/regions, create/reassign/deactivate members within the role hierarchy) |
| spoke-app | Coverage; Onboarding (classify + geofence); Sites; Site detail (**per-role guide — architect owns the BOM/design spec + phase schedule, CE executes, spokesperson owns coverage**; enter/edit product BOM, per-phase start/end dates, approve CE date changes, **confirm delivery**, notifications, start/complete phase/backfill) |
| consumer-portal | Projects, phase timeline + delivery status (**product names**), **Pay for project** (price BOM at tier → pay) |

`hub-console` gains `getUser().role`-aware UI (operator vs approver). Both hub-console and spoke-app share
a `PHASE_NAMES` map and the notifications/approval flows.

---

## 9. Configuration

- **Catalog & BOM** — 20 material categories + ~125 branded products seeded in inventory (structural 5 carry `per_sqft` for the auto-plan; finishing/MEP/interior categories use `per_sqft=0` and dispatch via an explicit BOM phase); 9 phases + weight matrix in site (`bom.py`); construction-type multipliers in code. Stock is **not** seeded (it comes from received POs).
- **Consumer** — carries `is_nbfc` (captured at spoke onboarding), cascaded to the admin Projects view + spoke customer list.
- **Pricing** — margin rules seeded (global 12%, per-tier 18/12/9/10, cement+individual 20%); product margins are set by the manager at runtime.
- **Scheduler** — `SCHEDULER_ENABLED` (default true) + `SCHEDULER_INTERVAL_SECONDS` (default 60) for the site-service JIT thread.
- **Web scout** — `SCOUT_PROVIDER` (auto/tavily/web/llm/stub) + `SCOUT_API_KEY` (e.g. Tavily) in `infra/.env`.
- **Payments** — provider + API bases + secret **env-var names** in `payment-service/config.yaml`; secrets in env.
- **AI + secrets** — `infra/.env` (gitignored): `JWT_SECRET`, `AI_PROVIDER/AI_API_KEY/AI_MODEL`, `SCOUT_*`, gateway/provider secrets.
- **Ports & URLs** — see [SLD.md](./SLD.md).

---

*Related: [HLD.md](./HLD.md) · [SLD.md](./SLD.md) · [DECISIONS.md](./DECISIONS.md)*
