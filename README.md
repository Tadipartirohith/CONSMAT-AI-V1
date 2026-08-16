# Consmat AI — V1 (Hub-and-Spoke)

> **Status:** 🟡 Design phase — this repository is a clean-slate rebuild. Code is added step by step as
> each design area is confirmed. See [`docs/`](./docs) for the design and [`docs/DECISIONS.md`](./docs/DECISIONS.md)
> for open questions and decisions.

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
| `backend/` | Backend service(s) — *to be built* |
| [`apps/hub-console/`](./apps/hub-console) | Hub operations console (supervisor + manager) — ✅ built (React/Vite) |
| `apps/spoke-app/` | Spoke app (spokesperson + architect + civil engineer) — *to be built* |
| `apps/consumer-portal/` | Retail consumer portal — *to be built* |
| `infra/` | Deployment (Docker Compose, etc.) — *to be built* |

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
8. 🟡 **Frontends** — ✅ hub-console (inventory/vendors/procurement+LLM/pricing, React/Vite/Tailwind, served on `:8095`); spoke-app + consumer-portal next.
