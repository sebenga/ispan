# iSpan Payments

Money is stored as integer **cents (ZAR)**. Never use floats.

## Providers

- **`MockProvider`** — default for development and the free MVP. Test-mode banner in the app.
- Placeholders (not live): PayFast, Yoco, Paystack, Ozow.

## Escrow (digital)

`pending → held → released_to_worker` or `refunded`.

Auto-release after a configurable window (suggested start: 24 hours after `completed`) if there is no dispute.

## Cash

No card capture. Commission and late-cancellation fees become **worker debt**, shown in the wallet, and may block new accepts above a threshold (suggested start: R150).

## Commission

Configurable per category in basis points. Suggested start: **12.5%**, labelled as a suggestion in seed/admin.

## Cancellation fee split

Documented clearly at booking (CPA). Exact ledger split is implemented in Phase 4; calculation snapshots exist from Phase 2.
