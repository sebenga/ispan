# iSpan Product Notes

Standalone “Uber for labour” marketplace. Launch city: **Cape Town**, with cities and countries modelled as data (not hard-coded exclusivity).

## Principles

1. Trust first — verification and escrow.
2. Worker dignity — independent contractors set rates and availability.
3. Low data / cheap phones.
4. Safety for both sides.
5. Configurable commercial rules in admin catalogues.
6. Privacy by design.

## Suggested starting points (admin-editable)

| Setting | Suggested start |
|---|---|
| Commission | 12.5% (1250 bps) |
| Late cancellation fee | 50% after notice window |
| Cancellation window | 2 hours before scheduled start |
| Offer timer | 20 seconds |
| Initial match radius | 5 km |
| Escrow auto-release | 24 hours after completed |
| Cash debt block | R150 |
| Minimum payout | R100 |

## Future (out of MVP scope)

- USSD access for feature phones
- Live PayFast / Yoco / Paystack / Ozow (placeholders only now)
- Partner insurance / training / financial products (feature-flagged referrals)

## Decisions log

- Phase 0 uses SQLite when `DATABASE_URL` is empty for fastest local boot; Compose Postgres is preferred for parity.
- Ionicons are registered via `addIcons` in `app.component.ts`.
