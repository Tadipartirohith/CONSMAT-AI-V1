# identity-service

Users, roles, and **JWT issuance** for Consmat AI V1 (resolves Q12). This service issues tokens;
every other service **validates** them locally with the shared `JWT_SECRET` (HS256) — no per-request
call back to identity.

## Roles
`admin · hub_manager · hub_supervisor · spokesperson · architect · civil_engineer · consumer · vendor`
(plus `service`, reserved for internal service-to-service tokens minted by the other services).

## Token claims
`{ sub: email, role, name, org_ref, iat, exp }` — `org_ref` links the user to their domain entity
(spoke_id / consumer_id / vendor_id).

## API (`/api/v1`)
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/login` | none | `{email,password}` → `{access_token, user}` |
| GET | `/auth/me` | bearer | Current user from token |
| GET | `/users` | admin/manager | List users |
| POST | `/users` | admin/manager | Create user |

## Demo users (password `consmat123`)
`admin@consmat.com` (admin) · `manager@consmat.com` (hub_manager) · `supervisor@consmat.com`
(hub_supervisor) · `spoke@consmat.com` (spokesperson) · `architect@consmat.com` (architect) ·
`civil@consmat.com` (civil_engineer) · `demo@consmat.com` (consumer) · `vendor@consmat.com` (vendor).

## Run (via infra compose)
```bash
docker compose -f infra/docker-compose.yml up -d --build
# identity-service → http://localhost:8005  (docs at /docs)
```
