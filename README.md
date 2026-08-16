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
| `apps/hub-console/` | Hub operations console (supervisor + manager) — *to be built* |
| `apps/spoke-app/` | Spoke app (spokesperson + architect + civil engineer) — *to be built* |
| `apps/consumer-portal/` | Retail consumer portal — *to be built* |
| `infra/` | Deployment (Docker Compose, etc.) — *to be built* |

## Design documents

- [**HLD**](./docs/HLD.md) — High-Level Design: architecture, actors, flows, modules.
- [**LLD**](./docs/LLD.md) — Low-Level Design: domain & role model (first cut), phases, LLM procurement.
- [**SLD**](./docs/SLD.md) — System-Level Design: deployment landscape, persistence, integrations.
- [**DECISIONS**](./docs/DECISIONS.md) — decision log and open questions.

## Build roadmap (one step at a time)

1. **Domain & role model** ← current — entities, roles, phases, relationships.
2. **Hub inventory** — inbound/outbound ledger, stock levels, valuation.
3. **Vendor registry + price lists** — vendor list, add-vendor, pricing.
4. **Procurement + Hub LLM** — BOM → profitability, alternatives, market price-scouting.
5. **Site & phase management** — plans, per-phase BOM, phase updates, JIT dispatch.
6. **Spoke ops** — geofence, consumer intake & classification.
7. **Pricing & margin** — hub selling price.
8. **Frontends** — hub console, spoke app, consumer portal.
