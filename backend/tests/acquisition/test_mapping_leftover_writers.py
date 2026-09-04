"""MA-3 leftover mapping writers are fail-closed. Not Operator Gate PASS. Not MA-4."""

from fastapi import HTTPException

from backend.app.acquisition.mapping_leftover_writers import (
    INTAKE_FORM_MAPPING_EVALUATOR_RETIRED,
    INTAKE_FORM_MAPPING_WRITES_RETIRED,
    META_MAPPING_WRITES_RETIRED,
    mapping_workspace_path,
    raise_intake_form_mapping_evaluator_retired,
    raise_intake_form_mapping_writes_retired,
    raise_meta_mapping_writes_retired,
)


def test_mapping_workspace_path() -> None:
    assert mapping_workspace_path() == "/app/marketing/sources"
    assert mapping_workspace_path("src-1") == "/app/marketing/sources/src-1/mapping"


def test_intake_form_mapping_put_is_leftover_writer() -> None:
    try:
        raise_intake_form_mapping_writes_retired(
            mapping_path="/app/marketing/sources/src-1/mapping",
        )
    except HTTPException as exc:
        assert exc.status_code == 410
        assert exc.detail["code"] == INTAKE_FORM_MAPPING_WRITES_RETIRED
        assert exc.detail["mapping_path"] == "/app/marketing/sources/src-1/mapping"
    else:
        raise AssertionError("expected leftover writer 410")


def test_intake_form_mapping_test_ingest_is_leftover_competing_create() -> None:
    try:
        raise_intake_form_mapping_evaluator_retired(
            mapping_path="/app/marketing/sources/src-1/mapping",
        )
    except HTTPException as exc:
        assert exc.status_code == 410
        assert exc.detail["code"] == INTAKE_FORM_MAPPING_EVALUATOR_RETIRED
        assert exc.detail["mapping_path"] == "/app/marketing/sources/src-1/mapping"
    else:
        raise AssertionError("expected leftover competing create 410")


def test_meta_mapping_put_is_leftover_writer() -> None:
    try:
        raise_meta_mapping_writes_retired()
    except HTTPException as exc:
        assert exc.status_code == 410
        assert exc.detail["code"] == META_MAPPING_WRITES_RETIRED
        assert exc.detail["mapping_path"] == "/app/marketing/sources"
    else:
        raise AssertionError("expected leftover writer 410")
