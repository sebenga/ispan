# iSpan Compliance Notes

**This is not legal advice.** Have a South African attorney review every item below before launch.

## Attorney checklist

- [ ] POPIA: Information Officer named; consent flows; retention schedule; operator list; Frankfurt cross-border clause `[cross-border transfer clause]`
- [ ] FICA / KYC: which document types may be onboarded (SA ID, passport, asylum/refugee permits); payout gates
- [ ] CPA: late-cancellation fee reasonableness and disclosure timing
- [ ] ECTA: company particulars on the notice page
- [ ] Labour: **This classification and the platform’s control features must be reviewed by a South African labour attorney before launch.** Workers are independent contractors, not employees.
- [ ] SANS 10142 / restricted trades: electrical CoC and wireman’s licence rules; plumbing PIRB where required
- [ ] Marketing claims: no invented market statistics

## Placeholders for counsel

| Placeholder | Where used |
|---|---|
| `[full legal name]` | Terms, ECTA notice |
| `[registration number]` | Terms, ECTA notice |
| `[directors]` | ECTA notice |
| `[physical address]` / `[postal address]` | ECTA notice |
| `[email]` / `[telephone]` | ECTA notice |
| `[VAT number if registered]` | ECTA notice |
| `[Information Officer name, email, phone]` | Privacy notice |
| `[cross-border transfer clause]` | Privacy notice |
| Retention periods in square brackets | Privacy notice |

## Product safeguards already designed in

- Legal consent gate with versioning (`LEGAL_VERSION`)
- Escrow until job confirmation
- Workers set their own rates; platform only suggests bands
- Declining an offer is not a strike
- GPS only during active job statuses (enforced from Phase 3)
- Identity documents encrypted at rest (Phase 1)
- Restricted trade certificate gates (Phase 2)
