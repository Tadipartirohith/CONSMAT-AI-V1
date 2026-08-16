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
| Q2 | Exact phase→material weight matrix (how each material's total splits across the 9 phases) | BOM/JIT | Step 5 |
| Q3 | Margin model: flat %, per-consumer-tier %, or per-material? | Pricing | Step 7 |
| ~~Q4~~ | ~~Backend shape~~ → **Resolved: microservices (D8)** | Architecture | ✅ |
| ~~Q5~~ | ~~DB & migrations~~ → **Resolved: SQLAlchemy 2.0 + Alembic + Postgres (D9)** | Persistence | ✅ |
| Q11 | Material/catalog ownership: which service owns the materials reference data (inventory-service provisionally; extract a catalog-service later?) | Architecture | Step 3 |
| Q12 | Inter-service auth: shared-secret JWT validated per service vs a dedicated identity-service issuing tokens | Security | Step 3 |
| Q6 | Is the consumer portal in V1 scope, or spoke-mediated only at first? | Frontends | Step 8 |
| Q7 | Site geolocation & spoke geofencing method (how a site maps to a spoke) | Spoke ops | Step 6 |
| Q8 | Procurement approval workflow (auto vs manual, and who) | Procurement | Step 4 |
| Q9 | Materials catalog beyond the 5 base items (tiles, cement types, MEP) | Catalog | later |
| Q10 | Credit terms per consumer tier | Pricing/finance | later |

---

## Change history
- **2026-08-16** — Initial pivot from V0 buyer-centric marketplace to V1 hub-and-spoke; D1–D7 confirmed.
