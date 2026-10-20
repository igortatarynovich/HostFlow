"""TikTok form list and lead CSV parsing. No database."""

from backend.app.modules.leads.tiktok_connection import (
    TikTokConnectionError,
    csv_text_to_tiktok_bodies,
    parse_instant_forms,
)


def test_parse_instant_forms_reads_page_list():
    forms = parse_instant_forms(
        {
            "code": 0,
            "data": {"list": [{"page_id": "998877", "title": "Drivers"}]},
        }
    )
    assert [(form.page_id, form.name) for form in forms] == [("998877", "Drivers")]


def test_parse_instant_forms_rejects_tiktok_error():
    try:
        parse_instant_forms({"code": 40001, "message": "invalid token"})
    except TikTokConnectionError as exc:
        assert exc.message == "invalid token"
    else:
        raise AssertionError("expected TikTokConnectionError")


def test_csv_text_to_tiktok_bodies_skips_reserved_columns():
    bodies = csv_text_to_tiktok_bodies(
        "lead_id,email,form_id\n55,a@b.c,998877\n",
        page_id="998877",
    )
    assert len(bodies) == 1
    entry = bodies[0]["entry"][0]
    assert entry["id"] == "55"
    assert entry["page_id"] == "998877"
    assert entry["changes"] == [{"field": "email", "value": "a@b.c"}]


def test_csv_text_to_tiktok_bodies_ignores_json():
    assert csv_text_to_tiktok_bodies('{"code":0}', page_id="1") == []
