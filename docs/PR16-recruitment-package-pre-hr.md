# PR16 — Recruitment package / pre-HR readiness

**Status:** Implemented (dossier-aligned package gate + candidate API + recruitment UX).

Build candidate document **and data** package before HR handoff; gate `ready_for_handoff` and handoff create on dossier blocks.

## Delivered

- `GET /api/v1/candidates/:id/recruitment-package` — block statuses aligned with HR dossier
- Gate extension: **Contacts & address** (phone, email, address) blocks stage + handoff when incomplete
- `create_handoff` validates package before client/internal transfer
- Frontend: `RecruitmentDossierChecklist` reads API; per-block **Confirm reviewed** (stored in `extra.recruitment_dossier_confirmed_blocks`)
- Handoff button + modal disabled until `pkg.ready` and all ready blocks confirmed
- Stage `ready_for_handoff` blocked client-side when package incomplete
- Tests: `test_recruitment_package_readiness.py`, handoff gate seeds (contact-aware)

## References

- [hr-employee-dossier.md](specs/frontend/hr-employee-dossier.md)
- `backend/app/services/recruitment_package_readiness.py`
