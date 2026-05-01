"""Единая матрица ролей для recruitment CRM (кандидаты, профили, связанные чтения).

Согласовано с docs/specs/architecture/rbac_matrix.md и docs/specs/rules.md:
- просмотр кандидатов в пределах ACL — в т.ч. viewer, client_* , compliance;
- hr_officer сюда не входит — только workforce/handoff API;
- суперадмин/админ тенанта по-прежнему обходят ограничения через resolve_candidate_acl (unrestricted).

Детальная фильтрация данных — в resolve_candidate_acl / ensure_candidate_access, не в списке имён ролей.
"""

from __future__ import annotations

from backend.app.auth.deps import Role

HIRING_CANDIDATE_VIEW_ROLES = (
    Role.superadmin,
    Role.administrator,
    Role.supervisor,
    Role.manager,
    Role.recruiter,
    Role.compliance_officer,
    Role.client_manager,
    Role.client_processor,
    Role.viewer,
)

HIRING_CANDIDATE_MUTATE_ROLES = (
    Role.manager,
    Role.admin,
    Role.recruiter,
    Role.compliance_officer,
    Role.administrator,
)

HIRING_CANDIDATE_PROFILE_READ_ROLES = HIRING_CANDIDATE_VIEW_ROLES

HIRING_CANDIDATE_PROFILE_WRITE_ROLES = (Role.admin, Role.supervisor)
