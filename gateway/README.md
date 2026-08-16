# gateway

The API gateway — a single nginx ingress in front of every backend microservice. It gives the platform
one API base URL and a central place for cross-cutting concerns (CORS today; rate limiting, request
logging, and edge auth checks are natural next additions).

## Routes
| Prefix | Service |
|--------|---------|
| `/api/identity/*` | identity-service `/api/v1` |
| `/api/inventory/*` | inventory-service `/api/v1` |
| `/api/procurement/*` | procurement-service `/api/v1` |
| `/api/site/*` | site-service `/api/v1` |
| `/api/pricing/*` | pricing-service `/api/v1` |
| `/api/payment/*` | payment-service `/api/v1` |

Plus `GET /` (route index) and `GET /health`.

## Traffic flow
All three frontends' nginx now proxy their API paths to the gateway (e.g. hub-console `/inv/*` →
`gateway/api/inventory/*`), so **every API request flows through the gateway** — it is the real
ingress, not a parallel entry. External/programmatic clients can call it directly with CORS.

```
browser → app nginx (static + /xxx proxy) → gateway → service
curl / external → gateway → service
```

## Run (via infra compose)
```bash
docker compose -f infra/docker-compose.yml up -d --build
# gateway → http://localhost:8080  (try /health, /, /api/identity/auth/login)
```
