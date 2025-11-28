from __future__ import annotations

from datetime import date, timedelta

from mock_repo import InMemoryDocsRepo
from owner_summary import compute_owner_summary
from rules_engine import compute_candidate_checklist, load_ruleset
from types_py import Document, OwnerContext, OwnerRef


def run():
    rs = load_ruleset("data/sample_ruleset.json")

    # 1) Контекст кандидата
    ctx = OwnerContext(
        citizenship="PL",
        residency_status="eu_citizen",
        vacancy={"requires_driver_attestation": False},
    )

    # 2) Получили чек-лист для required/optional
    checklist = compute_candidate_checklist(
        {
            "citizenship": ctx.citizenship,
            "residency_status": ctx.residency_status,
            "vacancy": ctx.vacancy,
        },
        rs,
    )
    print("Checklist:", checklist)

    # 3) Храним документы в in-memory репо
    repo = InMemoryDocsRepo()
    owner = OwnerRef(type="candidate", id="cand_123")

    # создаём два документа (identity_document + code95)
    _d1 = repo.create(
        Document(
            id="",
            tenant_id="t1",
            type_code="identity_document",
            owner=owner,
            status="approved",
            expires_at=(date.today() + timedelta(days=10)),
            title="Passport John Doe",
        )
    )
    _d2 = repo.create(
        Document(
            id="",
            tenant_id="t1",
            type_code="code95",
            owner=owner,
            status="approved",
            expires_at=(date.today() + timedelta(days=120)),
            title="Code 95",
        )
    )

    # 4) Получаем документы для owner и считаем сводку
    docs = repo.list_by_owner(owner)
    # приводим к «plain dict», с ключами, ожидаемыми owner_summary
    docs_plain = []
    for d in docs:
        docs_plain.append(
            {
                "type": d.type_code,
                "status": d.status,
                "issued_at": d.issued_at.isoformat()
                if isinstance(d.issued_at, date)
                else None,
                "expires_at": d.expires_at.isoformat()
                if isinstance(d.expires_at, date)
                else None,
            }
        )

    out = compute_owner_summary(
        {
            "citizenship": ctx.citizenship,
            "residency_status": ctx.residency_status,
            "vacancy": ctx.vacancy,
        },
        rs,
        docs_plain,
    )
    print("Summary:", out)


if __name__ == "__main__":
    run()
