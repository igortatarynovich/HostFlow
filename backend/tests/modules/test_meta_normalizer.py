from backend.app.modules.leads import normalizer


def _make_payload(field_data):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "leadgen_id": "123",
                            "field_data": field_data,
                        }
                    }
                ]
            }
        ]
    }


def test_normalize_meta_payload_accepts_phone_aliases():
    payload = _make_payload(
        [
            {"name": "phone_number", "values": ["+48 504 004 622"]},
            {"name": "full_name", "values": ["Igor Tatarynowicz"]},
            {"name": "country", "values": ["pl"]},
        ]
    )

    data = normalizer.normalize_meta_payload(payload)

    assert data["phone"] == "+48504004622"
    assert data["phone_country_code"] == "+48"
    assert data["full_name"] == "Igor Tatarynowicz"
    assert data["country"] == "PL"


def test_normalize_meta_payload_accepts_cyrillic_aliases():
    payload = _make_payload(
        [
            {"name": "телефон", "values": ["(068) 123-45-678"]},
            {"name": "имя", "values": ["Ivan"]},
            {"name": "фамилия", "values": ["Petrov"]},
        ]
    )

    data = normalizer.normalize_meta_payload(payload)

    assert data["phone"] == "+06812345678"
    assert data["first_name"] == "Ivan"
    assert data["last_name"] == "Petrov"


def test_normalize_meta_payload_invalid_phone_returns_none():
    payload = _make_payload(
        [
            {"name": "phone", "values": ["123"]},
        ]
    )

    data = normalizer.normalize_meta_payload(payload)

    assert data["phone"] is None


def test_normalize_meta_payload_parses_ag_ad_id_from_field_data():
    payload = _make_payload(
        [
            {"name": "ad_id", "values": ["ag:120245661643030547"]},
            {"name": "email", "values": ["a@example.com"]},
        ]
    )
    data = normalizer.normalize_meta_payload(payload)
    assert data["ad_id"] == 120245661643030547


def test_normalize_meta_payload_graph_error_propagates():
    payload = _make_payload(
        [
            {"name": "email", "values": ["test@example.com"]},
        ]
    )
    payload["entry"][0]["changes"][0]["value"]["graph_error"] = "GRAPH_190"

    data = normalizer.normalize_meta_payload(payload)

    assert data["graph_error"] == "GRAPH_190"


def test_phone_alias_plain_phone_key():
    payload = _make_payload(
        [
            {"name": "phone", "values": ["+1 (212) 555-7788"]},
        ]
    )

    data = normalizer.normalize_meta_payload(payload)

    assert data["phone"] == "+12125557788"


def test_contact_method_alias_is_captured():
    payload = _make_payload(
        [
            {"name": "preferred_contact", "values": ["WhatsApp"]},
            {"name": "Phone_Number", "values": ["+48504004622"]},
        ]
    )

    data = normalizer.normalize_meta_payload(payload)

    assert data["phone"] == "+48504004622"
    assert data["preferred_contact"] == "whatsapp"


def test_case_insensitive_keys_are_supported():
    payload = _make_payload(
        [
            {"name": "Phone_Number", "values": ["+49 151 234 5678"]},
            {"name": "COUNTRY", "values": ["de"]},
            {"name": "Full_Name", "values": ["Anna Schmidt"]},
        ]
    )

    data = normalizer.normalize_meta_payload(payload)

    assert data["phone"] == "+491512345678"
    assert data["country"] == "DE"
    assert data["full_name"] == "Anna Schmidt"
