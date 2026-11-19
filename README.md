# iSpan

Digital marketplace connecting South African customers with independent tradespeople (Cape Town first). Workers are **independent contractors**, not employees of iSpan.

## Stack

Django + DRF · Node Socket.IO · Ionic/Angular/Capacitor · Postgres · Valkey · Render (Frankfurt)

## Local setup

```bash
cd ispan
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env

# Infrastructure
make up                 # Postgres :5433, Valkey :6380

# API
cd backend && ../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py seed_demo

# App processes (API :8001, realtime :4000, Ionic :8100)
cd .. && ./scripts/dev-up.sh
# or: make dev
```

Open **http://localhost:8100/** — you should see the **legal consent gate**, then login.

### Health

- http://localhost:8001/healthz
- http://localhost:4000/healthz

### Demo logins (development only)

| Role | Email | Password |
|---|---|---|
| Customer | `customer@ispan.test` | `password123` |
| Electrician (verified + CoC) | `worker@ispan.test` | `password123` |
| Cleaner | `cleaner@ispan.test` | `password123` |
| Cleaner 2 (race tests) | `cleaner2@ispan.test` | `password123` |
| Plumber (no PIRB) | `plumber@ispan.test` | `password123` |
| Plumber (PIRB) | `plumber_certified@ispan.test` | `password123` |
| Admin | `admin@ispan.test` | `password123` |

## Tests

```bash
make test
# or:
cd backend && ../.venv/bin/python -m pytest
```

## Deploy (Render Frankfurt)

Use the Blueprint in `render.yaml` (New → Blueprint). Free-tier limits are documented in `docs/ARCHITECTURE.md`.

## Docs

- `docs/ARCHITECTURE.md`
- `docs/PRODUCT.md`
- `docs/PAYMENTS.md`
- `docs/COMPLIANCE.md` — attorney review checklist; replace all `[bracketed]` placeholders before production.

## Phases

This repo follows the phased build plan in the product brief.

- **Phase 0** — scaffold, legal gate, health checks, Blueprint, docs
- **Phase 1** — registration, mock OTP, JWT, dual profiles, verification queue
- **Phase 2** — category tree, jobs, matching (offers/race/radius), quotes, cancellation snapshots
- **Phase 3** — Socket.IO GPS/chat/SOS, navigation deep links, location status guards
- **Phase 4** — mock escrow/cash, wallets, payouts, receipts, auto-release
