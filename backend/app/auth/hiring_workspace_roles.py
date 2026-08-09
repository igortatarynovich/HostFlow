"""Единая матрица ролей для recruitment CRM (кандидаты, профили, связанные чтения).

Согласовано с ADR-036 / docs/specs/architecture/rbac_matrix.md:
- канонические trust: administrator / employee / viewer (+ superadmin bypass);
- legacy job/portal strings остаются в кортежах до Phase 3 enum cleanup;
- ``require_roles`` расширяет JOB_PROXY → employee и PORTAL_LEGACY → viewer+portal;
- hr_officer — доступ к карточке кандидата только в контексте internal-HR handoff
  (см. ``ensure_candidate_access`` / bypass recruitment lock в PATCH);
- суперадмин/админ тенанта по-прежнему обходят ограничения через resolve_candidate_acl.

Детальная фильтрация данных — в resolve_candidate_acl / ensure_candidate_access, не в списке имён ролей.
"""

from __future__ import annotations

from backend.app.auth.deps import Role

HIRING_CANDIDATE_VIEW_ROLES = (
    Role.superadmin,
    Role.administrator,
    Role.employee,  # ADR-036 canonical operational trust
    Role.viewer,
    # legacy JOB_PROXY / PORTAL_LEGACY (inventory → migrated via require_roles bridges)
    Role.supervisor,
    Role.manager,
    Role.recruiter,
    Role.compliance_officer,
    Role.client_manager,
    Role.client_processor,
    Role.hr_officer,
)

HIRING_CANDIDATE_MUTATE_ROLES = (
    Role.administrator,
    Role.admin,
    Role.employee,
    Role.manager,
    Role.recruiter,
    Role.compliance_officer,
    Role.hr_officer,
)

HIRING_CANDIDATE_PROFILE_READ_ROLES = HIRING_CANDIDATE_VIEW_ROLES

HIRING_CANDIDATE_PROFILE_WRITE_ROLES = (
    Role.admin,
    Role.administrator,
    Role.employee,  # team leads / supervisors migrate here + org scope
    Role.supervisor,
)
