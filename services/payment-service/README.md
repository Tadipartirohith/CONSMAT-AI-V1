# payment-service

Config-driven payment gateway for Consmat AI V1. The active provider and each provider's **API base URL
+ the env-var names for its secrets** live in [`config.yaml`](./config.yaml); the secret **values** stay
in the environment (`.env`), never in the file.

## Stack
FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL (own database, per D10) · PyYAML for gateway config.

## Providers
`mock` (default — settles locally, no network) · `razorpay` · `stripe` · `payu` · `cashfree`. Switch by
editing `payments.provider` in `config.yaml`. Real providers read their keys from the env vars named in
their config block; until those are set, payments create a *pending* intent and say so.

## Data model
- **payments** — `ref` (what's paid for, e.g. `SITE-1`), `consumer_id`, `amount`, `currency`,
  `provider`, `provider_ref`, `status` (pending|paid|failed|refunded), timestamps.

## API (`/api/v1`)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/payments/config` | Active provider + currency (non-secret) |
| POST | `/payments` | Create a payment (mock settles immediately) |
| POST | `/payments/{id}/confirm` | Confirm a pending payment |
| GET | `/payments` | List (`?consumer_id`, `?ref`) |
| GET | `/payments/{id}` | One payment |

Auth: a payer (consumer) or hub/field staff may initiate; reads for any authenticated user.

## Run (via infra compose)
```bash
docker compose -f infra/docker-compose.yml up -d --build
# payment-service → http://localhost:8006  (docs at /docs)
```

## Adding a real gateway
1. Set `payments.provider` in `config.yaml` (e.g. `razorpay`).
2. Put the secret values in the environment under the names declared in that provider's block
   (e.g. `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`).
3. Implement the provider's API call in `app/payments.py` (marked extension point).
