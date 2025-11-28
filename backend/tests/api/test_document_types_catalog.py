import pytest


@pytest.mark.anyio
async def test_document_types_include_driver_catalog(client, manager_headers):
    resp = await client.get("/api/v1/db/document-types", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert isinstance(payload, list) and payload, "Expected non-empty document type list"

    codes = {item["code"] for item in payload}
    required_codes = {
        "driver_license",
        "code95",
        "tacho_card",
        "national_id",
        "passport",
        "residence_permit",
        "visa",
        "decision",
        "medical_certificate",
        "psych_tests",
        "adr",
        "work_permit",
        "driver_certificate",
        "additional_document",
    }
    assert required_codes.issubset(
        codes
    ), f"Missing document types: {required_codes - codes}"

    by_code = {item["code"]: item for item in payload}
    for key in ("driver_license", "passport", "work_permit"):
        meta = by_code[key].get("meta_schema") or {}
        assert meta.get("properties"), f"{key} meta schema must include properties"
        files = by_code[key].get("required_files") or {}
        assert files, f"{key} missing required_files payload"

    additional = by_code["additional_document"]
    assert additional.get("duplicate_policy") == "many_allowed"
    assert additional.get("orderable") is False
    assert by_code["driver_license"]["requested_from"] == "driver"
    assert by_code["work_permit"]["requested_from"] == "agency"
