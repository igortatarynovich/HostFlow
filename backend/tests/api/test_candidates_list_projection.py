"""Compact Candidates list SQL stays a page projection, not a full ORM load."""

from sqlalchemy.dialects import postgresql

from backend.app.api.v1.candidates.repo import build_compact_candidate_list_stmt


def _sql() -> str:
    stmt = build_compact_candidate_list_stmt(
        "9497fc29-6051-424d-9344-abb4aed9b110",
        {"is_client_tenant": False},
        "created_at",
        True,
        200,
        0,
        None,
        include_labels=True,
        include_docs=True,
    )
    return str(stmt.compile(dialect=postgresql.dialect()))


def test_compact_list_sql_is_a_column_projection():
    sql = _sql().lower()
    assert "candidates.note" not in sql
    assert "candidates.docs_progress" not in sql
    assert "candidates.languages" not in sql
    assert "companies_1" not in sql
    assert "vacancies_1" not in sql
    assert "bool_or" in sql
    assert sql.count("from document_entity_links") == 1
    assert "limit" in sql
    assert sql.lower().count("pg_input_is_valid(") == 1
    assert "candidates.personal_data," not in sql
    assert "candidates.contacts," not in sql
    assert "cand_page" in sql
