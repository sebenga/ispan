# iSpan Payments

Money is stored as integer **cents (ZAR)**. Never use floats.

## Providers

| Provider | Status |
|---|---|
| **MockProvider** | Default for development and the free MVP |
| PayFast | Placeholder — raises “not configured” |
| Yoco | Placeholder — raises “not configured” |
| Paystack | Placeholder — raises “not configured” |
| Ozow | Placeholder — raises “not configured” |

Set `PAYMENT_PROVIDER=mock` (default). The app shows a **Test mode** banner when mock is active.

### Mock test cards

| `test_card` | Behaviour |
|---|---|
| `succeed` | Immediate authorize + hold |
| `fail` | Declined; payment stays / becomes `FAILED`; job not paid |
| `insufficient_funds` | Declined with clear error |
| `webhook_delay` | Authorize only; hold arrives via signed/mock webhook |

Webhooks: `POST /api/v1/payments/webhooks/{provider}/` with idempotency via `event_id` / `X-Idempotency-Key`. Duplicate events do not double-credit.

## Escrow (digital)

Lifecycle: `PENDING → AUTHORIZED → HELD → RELEASED` (or `REFUNDED` / `PARTIALLY_REFUNDED` / `FAILED`).

1. Customer calls `POST /api/v1/jobs/{id}/pay/escrow/` with a test card.
2. Funds are **held** until the job is confirmed (or auto-released).
3. On customer **confirm** (or auto-release after `ESCROW_AUTO_RELEASE_HOURS`, default 24h post-`COMPLETED` with no dispute):
   - Worker wallet is credited **pending**, then moved to **available**.
   - Platform commission is snapshotted on the payment row (`commission_bps` / `commission_cents`).
4. A dispute sets `payment.frozen` (Phase 5) and blocks release.

Run auto-release: `python manage.py auto_release_escrow` (or admin mock console).

## Cash

No card capture. On confirm, **commission** is recorded as **worker debt**. Late-cancellation fees owed by the worker also increase debt.

When `debt_cents >= CASH_DEBT_BLOCK_CENTS` (suggested start **R150** / 15000 cents), the worker cannot accept new jobs until debt is cleared (e.g. deducted on payout).

## Payouts (FICA gate)

`POST /api/v1/wallets/me/payouts/`

- Blocked unless worker `verification_status=VERIFIED` and `bank_verified`.
- Minimum payout: `MIN_PAYOUT_CENTS` (suggested **R100**).
- Mock provider marks payout `PAID` and may clear outstanding debt from the withdrawn amount.

## Receipts

`GET /api/v1/jobs/{id}/receipt/` returns HTML + totals for the caller (customer or worker). Legal entity placeholders remain `[full legal name]` until counsel fills them.

## Cancellation fee settlement (Phase 4)

Uses the **snapshotted** policy on the job (Phase 2):

- **Customer late cancel (escrow):** refund = amount − fee; worker may receive fee − commission; platform keeps commission on the fee.
- **Worker late cancel:** full escrow refund to customer; fee recorded as worker debt (cash or digital).
- Free cancel while still matching (`REQUESTED` / `OFFERED` / `QUOTED`): fee = 0.

## Admin mock console

Staff: `GET/POST /api/v1/admin/payments/mock/`

- List recent payments and webhook events.
- `action=fire_webhook` to complete a `webhook_delay` payment.
- `action=auto_release` to sweep due holds.

## Commission

Configurable per category in basis points. Suggested start: **12.5% (1250 bps)** — labelled as a suggestion in catalogue seed/admin, not a hard market claim.
