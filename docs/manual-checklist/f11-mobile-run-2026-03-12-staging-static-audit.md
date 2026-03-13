# F11 Mobile Run Record

Date: `2026-03-12`  
Environment: `staging`  
Tenant: `static-audit`  
Owner: `Product/QA`  
Result: `FAIL`  
Decision: `NO-GO`  
Blockers: `Manual device QA for iOS Safari/Android Chrome not executed yet; final PASS is blocked until device-level evidence is collected.`

## Device Matrix

- iOS Safari: `NOT_EXECUTED`
- Android Chrome: `NOT_EXECUTED`
- Desktop emulation: `static code/UI audit only (no interactive device run)`

## Route/Breakpoint Results

| Route | 320 | 375 | 390 | 768 | Notes | Evidence |
|---|---|---|---|---|---|---|
| `/` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L534) |
| `/signup` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L535) |
| `/app/onboarding/company` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L537) |
| `/app/onboarding/getting-started` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L538) |
| `/app/overview` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L539) |
| `/app/clients` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L540) |
| `/app/leads` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L541) |
| `/app/messages` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L542) |
| `/app/reminders` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L543) |
| `/public/scan` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L544) |
| `/app/settings` | `PASS` | `PASS` | `PASS` | `PASS` | Static pass per SSOT matrix (`PASS_STATIC` baseline). | [crm-production-readiness-ssot.md](/opt/HostFlow/docs/crm-production-readiness-ssot.md#L545) |

## Touch/Keyboard/Modal Audit

- Touch target baseline (`>=44px`): `PASS (static)`; based on global control baseline and modal updates already documented in `5.6.6/5.6.7`.
- Soft keyboard overlap (`iOS/Android`): `FAIL`; not verified on real devices.
- Modal scroll and sticky actions: `PASS (static)`; CSS/modal shell constraints present, but no real-device confirmation.
- Horizontal overflow check: `PASS (static)` for previously fixed `MOB-001..004`; full device confirmation pending.

## Summary Evidence

- Screenshots: `N/A (device run pending)`
- Videos: `N/A (device run pending)`
- Notes: `This record captures only static baseline and intentionally blocks final mobile PASS until manual device QA is completed.`

## Issues

- `MOB-MANUAL-001 (tracking placeholder): manual iOS/Android device QA evidence not collected yet.`

## Sign-off

- Product: `Pending after device run`
- QA: `Pending after device run`
