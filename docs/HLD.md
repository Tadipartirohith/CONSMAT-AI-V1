# Consmat AI V1 — High-Level Design (HLD)

> **Status:** 🟢 As-built · **Version:** 1.0 · **Model:** Hub-and-Spoke distribution
>
> This reflects the system as actually built and running. Decisions are logged in
> [DECISIONS.md](./DECISIONS.md) (D1–D13); detail is in [LLD.md](./LLD.md) and [SLD.md](./SLD.md).

---

## 1. Introduction

Consmat AI V1 is a **hub-and-spoke construction-materials distribution platform**. A central **hub**
procures, owns, prices, and dispatches material; geo-fenced **spokes** (field agents) manage retail
consumers and their construction sites; and material is delivered **just-in-time, phase by phase** as
each site progresses. The system is a set of **microservices** behind an **API gateway**, with three
role-specific React frontends.

**Core principle — deterministic money, AI assistance:** every price, quantity, stock level, margin, and
allocation is computed by deterministic services. A live LLM (Gemini) *advises* on procurement but never
sets a figure.

---

## 2. What's built (at a glance)

| Layer | Components |
|-------|-----------|
| **Ingress** | `gateway` (nginx) — single API entry, `/api/<service>/` routing, central CORS |
| **Services** | `identity` · `inventory` · `procurement` · `pricing` · `site` · `payment` (FastAPI + SQLAlchemy 2.0 + Alembic) |
| **Frontends** | `hub-console` · `spoke-app` · `consumer-portal` (React 18 + Vite + Tailwind, JWT login) |
| **Data** | one PostgreSQL, **database per service** |
| **AI** | Hub LLM = pluggable provider, running **live on Gemini** (`gemini-flash-lite-latest`) |

---

## 3. Confirmed Decisions (summary)

Full log in [DECISIONS.md](./DECISIONS.md). Highlights: **D1** hub owns inventory & prices, is also a
supplier and procures from vendors · **D2** single hub → many spokes · **D3** spokes hold no stock
(coordination role; goods ship hub → site) · **D4** 9-phase construction model drives JIT demand ·
**D5** 4-tier consumer classification · **D6** Hub LLM for procurement intelligence · **D7** persistent
DB · **D8/D9/D10** microservices, SQLAlchemy 2.0 + Alembic, database-per-service · **D11** config-driven
payments · **D12** Hub LLM on Gemini · **D13** API gateway.

---

## 4. Architecture

```mermaid
flowchart TB
    subgraph Users["Browsers"]
        U1["Hub staff<br/>(manager/supervisor)"]
        U2["Spoke team<br/>(spokesperson/architect/civil engr)"]
        U3["Consumer"]
    end

    subgraph Apps["Frontends (nginx-served SPAs)"]
        HC["hub-console :8095"]
        SA["spoke-app :8096"]
        CP["consumer-portal :8097"]
    end

    GW["API gateway :8088<br/>/api/&lt;service&gt;/ · CORS"]

    subgraph Svc["Services (FastAPI)"]
        ID["identity :8005"]
        INV["inventory :8001"]
        PROC["procurement :8002"]
        PRICE["pricing :8004"]
        SITE["site :8003"]
        PAY["payment :8006"]
    end

    DB[("PostgreSQL :5433<br/>db per service")]
    LLM["Gemini LLM"]

    U1-->HC
    U2-->SA
    U3-->CP
    HC-->|"/api"| GW
    SA-->|"/api"| GW
    CP-->|"/api"| GW
    GW-->ID & INV & PROC & PRICE & SITE & PAY
    ID & INV & PROC & PRICE & SITE & PAY --> DB

    PROC -. "inbound / selling-prices" .-> INV
    PROC -. "selling-prices" .-> PRICE
    SITE -. "catalog / outbound dispatch" .-> INV
    PRICE -. "avg cost" .-> INV
    PROC -. "advice" .-> LLM
```

> Frontend + external API traffic goes **through the gateway**. Internal service-to-service calls
> (dashed) go **directly** by service name, authenticated with a minted `service` token.

---

## 5. Actors & Roles

| Role | App | Responsibilities |
|------|-----|------------------|
| **hub_manager** | hub-console | Pricing/margins, approvals, vendor registry, procurement, staff |
| **hub_supervisor** | hub-console | Inventory movements, procurement runs, dispatch/receive |
| **spokesperson** | spoke-app | Geofence, consumer intake & 4-tier classification |
| **architect** | spoke-app | Site plans → BOM |
| **civil_engineer** | spoke-app | Phase progress updates (the JIT trigger) |
| **consumer** | consumer-portal | View own project, pay |
| **vendor** | (upstream) | Sells material to the hub |
| **admin** | any | Full override |
| *service* | — | Internal service-to-service token |

The **spoke-app** blends the three field roles into one guard set (any field role may perform field
actions); the **hub-console** distinguishes supervisor (ops) from manager (pricing/approvals).

---

## 6. Service Catalog

| Service | Owns | Key API |
|---------|------|---------|
| **identity** | Users, roles, JWT issuance | `/auth/login`, `/auth/me`, `/users` |
| **inventory** | Materials catalog, stock + append-only ledger | `/materials`, `/inventory*`, `/ledger` |
| **procurement** | Vendors + price lists, planning, Hub LLM, orders | `/vendors*`, `/prices/{m}`, `/procurement/*` |
| **pricing** | Margin rules, selling price | `/margins`, `/price/{m}`, `/quote`, `/selling-prices` |
| **site** | Spokes, consumers, sites, plans, phases, dispatch, backfill | `/spokes*`, `/consumers*`, `/intake`, `/sites*`, `/backfill` |
| **payment** | Config-driven gateway, payments | `/payments*`, `/payments/config` |

Full endpoint reference in [LLD §4](./LLD.md#4-api-reference).

---

## 7. Frontends

| App | For | Pages |
|-----|-----|-------|
| **hub-console** | supervisor/manager | Overview (+ network re-dispatch), Inventory, Vendors, Procurement (+ LLM advice), Pricing, Payments |
| **spoke-app** | spokesperson/architect/civil engineer | Territory, Intake, Sites, Site detail (plan/start/complete/backfill) |
| **consumer-portal** | consumer | Projects, phase timeline + delivery status, Pay for project |

All three: JWT login, token attached to every request, 401 → logout, role shown; API reaches services
through their own nginx → the gateway.

---

## 8. Core Flows

### 8.1 Supply (procurement) — LLM-advised

```mermaid
sequenceDiagram
    autonumber
    participant H as Hub (console)
    participant PR as procurement
    participant PC as pricing
    participant LLM as Gemini
    participant INV as inventory
    H->>PR: Analyze demand (tier)
    PR->>PR: cheapest-source plan (deterministic)
    PR->>PC: selling-prices(tier)
    PR->>LLM: advise on plan + profitability
    LLM-->>PR: summary · alternatives · flags (advice only)
    PR-->>H: plan + margin + advice
    H->>PR: Create order → Receive
    PR->>INV: inbound (per line) → stock + weighted-avg cost
```

### 8.2 Demand (phased JIT) & self-healing backfill

```mermaid
sequenceDiagram
    autonumber
    participant CE as Civil engineer (spoke-app)
    participant SITE as site
    participant INV as inventory
    participant HUB as Hub (console)
    CE->>SITE: Complete phase N
    SITE->>INV: outbound phase N+1 slice
    alt stock ok
        INV-->>SITE: dispatched
    else short
        INV-->>SITE: 409 → line marked short (demand signal)
    end
    HUB->>HUB: replenish (procurement → receive)
    HUB->>SITE: Re-dispatch shortfalls (/backfill)
    SITE->>INV: retry short lines → dispatched, dispatch healed
```

### 8.3 Money — pricing & consumer payment

```mermaid
sequenceDiagram
    autonumber
    participant C as Consumer (portal)
    participant PC as pricing
    participant INV as inventory
    participant PAY as payment
    C->>PC: quote(site BOM, my tier)
    PC->>INV: landed cost (avg_cost)
    PC-->>C: total = Σ(qty × cost × (1+margin))
    C->>PAY: pay(ref, amount)
    PAY-->>C: settled (mock gateway) → receipt
```

---

## 9. Authentication & Authorization

- **identity-service issues** JWTs (HS256) on login; claims: `sub` (email), `role`, `name`, `org_ref`.
- **Every service validates locally** with the shared `JWT_SECRET` — no call back to identity.
- **Role guards** per endpoint (reads: any authenticated; writes: role-scoped).
- **Service-to-service** calls mint a short-lived `service` token so internal flows (dispatch, receive,
  pricing) pass their targets' guards.

Detail in [LLD §5](./LLD.md#5-authentication--roles).

---

## 10. Cross-Cutting Concerns

- **Deterministic pricing** — all figures from services; the LLM only reasons over them.
- **Config-driven** — catalog/BOM coefficients seeded; payment providers in `config.yaml`; LLM + secrets in `.env`.
- **Single ingress** — the gateway centralizes API routing + CORS; a home for future rate limiting/edge auth.
- **Self-healing supply** — shortfalls are first-class signals; backfill reconciles them after replenishment.
- **Graceful AI degradation** — LLM error/quota → deterministic fallback, no failure.

---

## 11. Non-Functional Characteristics

| Attribute | As-built |
|-----------|----------|
| Persistence | PostgreSQL, database per service; durable ledger |
| Consistency | Inventory mutations row-locked + transactional; append-only ledger |
| Auth | JWT + role guards; shared secret; service tokens for internal calls |
| Scalability | Services independent; single hub simplifies v1; horizontal scale needs shared-nothing per service (already db-per-service) |
| Security | Secrets via env (gitignored); CORS at gateway; TLS is an ops add-on |
| AI | Live Gemini (free-tier quota); deterministic fallback |

---

## 12. Status & Remaining

**Complete:** all 8 build steps + auth + payments + API gateway + backfill; Hub LLM live.

**Deferred / optional:** real payment-provider API calls (extension points in `payment-service`), and
finer product questions in [DECISIONS.md](./DECISIONS.md) (approval thresholds, procurement approval
workflow, catalog expansion, credit terms). Production hardening (TLS, secrets manager, rate limiting)
is out of scope for v1.

---

*Related: [LLD.md](./LLD.md) · [SLD.md](./SLD.md) · [DECISIONS.md](./DECISIONS.md)*
