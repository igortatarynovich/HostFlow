# HR employee dossier (post-handoff verification UX)

**Status:** Implemented — canonical HR card layout after internal handoff.

## Product model

One human, two modules:

| Module | Surface | After handoff |
|--------|---------|---------------|
| Recruitment | `/app/candidates/:id` | Package checklist + handoff; read-only when `processing_by_hr` |
| HR | `/app/hr/employees/:id` | **Dossier** — verify blocks, eligibility, employment decision |

## Dossier block types

| Type | Example | File | Confirm |
|------|---------|------|---------|
| Document | Passport, Legal stay | Required | File + fields |
| Data only | Contacts & address | None | Fields only |
| Optional file | Work experience | Optional | Fields only |

## HR flow

1. Open employee card → **Verify documents and data**
2. Each block: fields, file actions, **Confirm data**; preview in right rail (desktop)
3. All blocks confirmed → **Next step** CTA (eligibility / employment decision)
4. **Case actions:** corrections, return to recruitment, reject
5. After approve → **Post-approval** onboarding tasks (collapsed)

## Recruitment symmetry (pre-handoff)

On candidate card at `docs_got` / `ready_for_handoff` / `processing_by_hr`:

- **Recruitment package** checklist — same logical blocks as HR dossier
- **Open in HR dossier →** when workforce employee exists (`processing_by_hr`)

## Key files

- Frontend: `EmployeeDossierView.tsx`, `EmployeeDossierDocumentBlock.tsx`, `RecruitmentDossierChecklist.tsx`
- Backend: `hr_verification_plan.py`, `hr_verified_field_catalog.py`, `hr_document_verification.py`
- Handoff mapping: `workforce_employees._candidate_snapshot`

## References

- [PR17-candidate-to-employee-handoff-spec.md](../../PR17-candidate-to-employee-handoff-spec.md)
