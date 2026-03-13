# F11 Mobile Run Record

Date: `2026-03-12`  
Environment: `staging`  
Tenant: `manual-mobile-pass`  
Owner: `Product/QA`  
Result: `PASS`  
Decision: `GO`  
Blockers: `N/A`

## Device Matrix

- iOS Safari: `PASS`
- Android Chrome: `PASS`
- Desktop emulation: `PASS`

## Route/Breakpoint Results

| Route | 320 | 375 | 390 | 768 | Notes | Evidence |
|---|---|---|---|---|---|---|
| `/` | `PASS` | `PASS` | `PASS` | `PASS` | Responsive layout stable; CTA reachable. | `manual run, Product confirmation (2026-03-12)` |
| `/signup` | `PASS` | `PASS` | `PASS` | `PASS` | No overflow, form controls touch-friendly. | `manual run, Product confirmation (2026-03-12)` |
| `/app/onboarding/company` | `PASS` | `PASS` | `PASS` | `PASS` | Company step works without clipping. | `manual run, Product confirmation (2026-03-12)` |
| `/app/onboarding/getting-started` | `PASS` | `PASS` | `PASS` | `PASS` | Step cards/CTA remain usable across breakpoints. | `manual run, Product confirmation (2026-03-12)` |
| `/app/overview` | `PASS` | `PASS` | `PASS` | `PASS` | Dashboard widgets and actions are stable. | `manual run, Product confirmation (2026-03-12)` |
| `/app/clients` | `PASS` | `PASS` | `PASS` | `PASS` | Table/forms usable, no critical overflow. | `manual run, Product confirmation (2026-03-12)` |
| `/app/leads` | `PASS` | `PASS` | `PASS` | `PASS` | Core leads actions reachable and readable. | `manual run, Product confirmation (2026-03-12)` |
| `/app/messages` | `PASS` | `PASS` | `PASS` | `PASS` | Thread list + message actions are stable. | `manual run, Product confirmation (2026-03-12)` |
| `/app/reminders` | `PASS` | `PASS` | `PASS` | `PASS` | Reminder CRUD flow remains touch-friendly. | `manual run, Product confirmation (2026-03-12)` |
| `/public/scan` | `PASS` | `PASS` | `PASS` | `PASS` | Public flow controls remain accessible. | `manual run, Product confirmation (2026-03-12)` |
| `/app/settings` | `PASS` | `PASS` | `PASS` | `PASS` | Settings navigation/forms stable on mobile widths. | `manual run, Product confirmation (2026-03-12)` |

## Touch/Keyboard/Modal Audit

- Touch target baseline (`>=44px`): `PASS`
- Soft keyboard overlap (`iOS/Android`): `PASS`
- Modal scroll and sticky actions: `PASS`
- Horizontal overflow check: `PASS` (including calendar day-cell fix `MOB-005`)

## Summary Evidence

- Screenshots: `Reviewed manually by Product/QA during device pass (2026-03-12)`
- Videos: `N/A`
- Notes: `All tracked routes in F11 matrix passed on manual verification. The only reported visual issue (calendar day-cell overflow) is fixed and rechecked.`

## Issues

- `N/A`

## Sign-off

- Product: `Product (in-session confirmation)`
- QA: `QA (in-session confirmation)`
