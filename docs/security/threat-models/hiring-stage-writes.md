# Threat Model — Hiring-path candidate stage writes (HE-2)

**Surface:** authenticated CRM candidate create / PATCH / stage move (`backend/app/api/v1/candidates/*`).  
**Not:** candidate portal, handoff, eligibility collapse (HE-3), RS-7, min HR.

## Assets

- Candidate occupancy (`Candidate.stage`) — CLASS 2 process state, not a public identity catalog.
- Stage existence answers on the hiring path (which codes may be written).

## Trust boundaries

- Authenticated recruiter / hiring-workspace actor (existing RBAC) ↔ tenant-scoped candidate row.
- Company Funnel configuration and tenant stage dictionaries are **leftover**. They must not mint a writable identity.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| HS-1 | Tenant-minted code as occupancy | Funnel-local / dictionary / short-list code accepted as `Candidate.stage` |
| HS-2 | IDOR on stage write | PATCH another tenant’s candidate (existing ACL / RLS; unchanged here) |
| HS-3 | Skip-eligibility via unregistered jump | Write a leftover-only or unknown code to bypass registered walk |
| HS-4 | New public write | Accidental unauthenticated stage endpoint (not introduced) |

## Митигации (HE-2)

- Existence on this path is **only** LI-1 `is_stage_registered("recruitment", "candidate", key)`.
- Occupancy remains **`Candidate.stage`**. Funnel ≠ occupancy (ADR-037).
- Unregistered / funnel-local / leftover-granted target → **422** (`Unknown stage`). Fail closed.
- Transition-order rule `forward_moves_guarded_jumps_rejected`: leftover-granted codes are jumps. Forward registered moves still hit leftover pipeline guards (HE-3 leftovers; not collapsed here).
- No new public route. No RLS / trust-role / portal / handoff change.

## Тесты

- Named Stage Authority Consumption Gate: registered keys accepted; `skontaktowac__sie_pozniej` / `offer` → 422.
- Hiring-path helpers must not query `FunnelStage` for existence.

## Связанные спеки

- [`hiring-stage-authority-consumption.md`](../../specs/architecture/hiring-stage-authority-consumption.md) (`hiring_stage_authority.v1`)
- [`hiring-acceptance-contract.md`](../../specs/architecture/hiring-acceptance-contract.md) (`hiring_acceptance.v1`)
- [`ADR-037`](../../specs/architecture/ADR-037-lifecycle-identity-canon.md)

## History

- 2026-09-21: HE-2 acknowledgement. Production candidate stage writes consume LI-1. Leftovers stop answering existence on this path.
