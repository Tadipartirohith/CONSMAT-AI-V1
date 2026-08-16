# Consmat AI V1 — Decision Log & Open Questions

A lightweight ADR-style log. **Confirmed** decisions are locked; **Open** items are resolved as we
design each roadmap step. Date format: YYYY-MM-DD.

---

## Confirmed decisions

| ID | Date | Decision | Rationale |
|----|------|----------|-----------|
| **D1** | 2026-08-16 | **Hub owns inventory & resells; hub sets price; hub is also a supplier and procures from external vendors** | Hub is the merchant of record and distribution authority (distributor model) |
| **D2** | 2026-08-16 | **Topology: single hub → many spokes** | Simplest realistic v1; generalizable later |
| **D3** | 2026-08-16 | **Spoke holds no stock; material ships hub → site; only the hub tracks inventory** | Spoke is a coordination/relationship role (a person), not a warehouse |
| **D4** | 2026-08-16 | **9-phase construction model drives phased JIT demand** | Precise just-in-time dispatch; matches site progression |
| **D5** | 2026-08-16 | **4-tier consumer classification: Individual · Contractor · Commercial · Government/Institutional** | Supports differentiated pricing/credit/priority |
| **D6** | 2026-08-16 | **Hub LLM for procurement intelligence** (profitability, alternatives, price-scouting) | Moves V0's LLM upstream to buying/pricing decisions |
| **D7** | 2026-08-16 | **Persistent database (PostgreSQL assumed) instead of in-memory** | Inventory ledger requires durability & auditability |
| **D8** | 2026-08-16 | **Microservices architecture** (one service per domain) | Resolves Q4; chosen over modular monolith for independent scaling/deploy |
| **D9** | 2026-08-16 | **Persistence stack: SQLAlchemy 2.0 + Alembic on PostgreSQL** | Resolves Q5; battle-tested ORM + migrations, transactional ledger |
| **D10** | 2026-08-16 | **Microservices conventions**: database-per-service, synchronous REST to start (events later), per-service FastAPI + Dockerfile + Alembic, API gateway deferred | Standard microservice defaults; keeps services independent |
| **D11** | 2026-08-16 | **Payments are config-driven**: provider (mock default) + each provider's API base URL and secret **env-var names** live in `payment-service/config.yaml`; secret values only in env. Real providers are extension points. | Swap gateways without code changes; keep keys out of the repo |
| **D12** | 2026-08-16 | **Hub LLM provider set to Gemini** via `infra/.env` (`AI_PROVIDER=gemini`, `AI_MODEL=gemini-flash-lite-latest`); goes live once an API key is added to `AI_API_KEY` | Enable procurement intelligence; key supplied by the operator, never committed |
| **D13** | 2026-08-16 | **API gateway built** (top-level `gateway/`, nginx): single ingress fronting all services under `/api/<service>/` with central CORS. All frontends repointed to route API traffic through it. Supersedes the "deferred" note in D10. | One API entry point + a home for cross-cutting concerns |
| **D16** | 2026-08-16 | **External price sources (price-scout).** procurement gains `external_offers` + a pluggable scout (`SCOUT_PROVIDER=auto/llm/stub`): the Hub LLM returns **indicative** internet prices (IndiaMART/TradeIndia style), and supplier price lists import as **firm** offers (`/external-offers/import`). External offers are **advisory** — the deterministic plan still buys from the registry; the LLM factors them into advice ("onboard cheaper supplier"). **No IndiaMART scraper** (no clean price API + ToS/anti-bot); real web-search (SerpAPI/Bing/Gemini-grounding) is a documented extension point. | Market intelligence without a fragile scraping foundation |
| **D15** | 2026-08-16 | **Procurement is tier-agnostic.** Buying doesn't depend on the consumer tier; `/procurement/analyze` no longer takes `tier`. Profitability is a reference lens computed against the hub **list price** (pricing-service, no tier), or an explicit `selling_prices` override. Removes the earlier tier smell. | Buying and selling are separate concerns |
| **D14** | 2026-08-16 | **Product/brand layer + full-name search.** Catalog (inventory) gains `products` (branded SKUs under a material); vendor pricing + procurement plans move to the product level (several companies per material); `GET /products/search?q=` does full product-name search. BOM and hub stock stay at material level. Partially resolves Q9. | Real procurement is brand-specific; buyers search by full product name |

### The 9 phases (per D4)
1. Excavation & footing
2. Foundation & plinth beam
3. RCC superstructure (repeats per floor)
4. Masonry / brickwork
5. Roofing / terrace slab
6. Internal plastering
7. External plastering
8. Flooring & tiling
9. MEP & finishing

---

## Open questions

| ID | Question | Affects | Target step |
|----|----------|---------|-------------|
| Q1 | Manager vs supervisor: which actions need manager approval, and value thresholds? | Roles/permissions | Step 1–3 |
| Q2 | Exact phase→material weight matrix — **default set in site-service `bom.py` (sums to 1.0/material); still tunable.** Per-floor RCC repetition modelled at building level for now. | BOM/JIT | 🟡 default set |
| ~~Q3~~ | ~~Margin model~~ → **Resolved: one margin-rule table with precedence (material+tier > material > tier > global > service-default). Supports flat, per-tier, and per-material at once.** | Pricing | ✅ |
| ~~Q4~~ | ~~Backend shape~~ → **Resolved: microservices (D8)** | Architecture | ✅ |
| ~~Q5~~ | ~~DB & migrations~~ → **Resolved: SQLAlchemy 2.0 + Alembic + Postgres (D9)** | Persistence | ✅ |
| ~~Q11~~ | ~~Material/catalog ownership~~ → **Resolved: inventory-service owns the catalog and exposes `GET /materials`; other services reference `material_id` as an opaque string (no cross-service FK). Extract a catalog-service later if it grows.** | Architecture | ✅ |
| ~~Q12~~ | ~~Inter-service auth~~ → **Resolved: BOTH — identity-service issues JWTs; every service validates locally with the shared JWT_SECRET (HS256); internal service-to-service calls use a minted `service` token.** Frontends log in and attach the token; role guards per endpoint. | Security | ✅ |
| Q6 | Is the consumer portal in V1 scope, or spoke-mediated only at first? | Frontends | Step 8 |
| ~~Q7~~ | ~~Site geolocation & spoke geofencing~~ → **Resolved: area-keyword matching (spoke covers keywords; location served by the spoke whose keyword appears, most-specific wins). Lat/lng deferred.** | Spoke ops | ✅ |
| Q8 | Procurement approval workflow (auto vs manual, and who) | Procurement | Step 4 |
| Q9 | Materials catalog beyond the 5 base items (tiles, cement types, MEP) | Catalog | later |
| Q10 | Credit terms per consumer tier | Pricing/finance | later |

---

## Change history
- **2026-08-16** — Initial pivot from V0 buyer-centric marketplace to V1 hub-and-spoke; D1–D7 confirmed.
