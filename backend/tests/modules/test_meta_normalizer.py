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


def test_normalize_meta_payload_maps_nazwa_firmy_and_preserves_field_answers():
    payload = _make_payload(
        [
            {"name": "full_name", "values": ["Dina Kurt"]},
            {"name": "email", "values": ["di555@o2.pl"]},
            {"name": "phone_number", "values": ["+48789186757"]},
            {"name": "nazwa_firmy", "values": ["Synergia Kadry"]},
            {"name": "kogo_obecnie_poszukujesz?", "values": ["kierowcy"]},
            {
                "name": "czy_prowadzisz_obecnie_płatne_kampanie_reklamowe?",
                "values": ["nie"],
            },
        ]
    )

    data = normalizer.normalize_meta_payload(payload)

    assert data["company_name_hint"] == "Synergia Kadry"
    assert data["company_name"] == "Synergia Kadry"
    assert data["company_profile"]["name"] == "Synergia Kadry"
    assert data["need"]["what_needed"] == "kierowcy"
    assert data["marketing"]["runs_paid_ads"] == "nie"
    assert data["contact_person"]["email"] == "di555@o2.pl"
    names = [row["name"] for row in data["field_answers"]]
    assert "nazwa_firmy" in names
    assert "kogo_obecnie_poszukujesz?" in names


def test_normalize_meta_payload_maps_danema_cyrillic_question_keys():
    payload = _make_payload(
        [
            {"name": "email", "values": ["driver@example.com"]},
            {
                "name": "основание_для_пребывания_в_польше",
                "values": ["karta_pobytu_(residence_card)"],
            },
            {"name": "опыт_работы_с/се_в_европе", "values": ["2 years"]},
        ]
    )

    data = normalizer.normalize_meta_payload(payload)

    assert data["poland_stay_basis"] == "karta_pobytu"
    assert data["poland_stay_basis_raw"] == "karta_pobytu_(residence_card)"
    assert data["driving_experience_in_europe"] == "2 years"


def _tiktok_lead_body():
    return {
        "request_id": "req-1",
        "object": 1,
        "time": 1743639757,
        "entry": [
            {
                "id": "7123456789012345678",
                "lead_source": "INSTANT_FORM",
                "page_id": "998877",
                "page_name": "Drivers PL",
                "advertiser_id": "7001",
                "ad_id": "1800000000000001",
                "create_time": 1743639757,
                "changes": [
                    {"field": "Name", "value": "Ivan Petrov"},
                    {"field": "Email", "value": "ivan@example.com"},
                    {"field": "Phone number", "value": "+48 504 004 622"},
                ],
            }
        ],
    }


def test_tiktok_lead_webhook_normalizes_like_meta():
    body = _tiktok_lead_body()
    assert normalizer.tiktok_lead_entry(body)["id"] == "7123456789012345678"
    coerced = normalizer.coerce_tiktok_lead_to_meta_payload(body)
    data = normalizer.normalize_meta_payload(coerced)
    assert data["raw_lead_id"] == "7123456789012345678"
    assert data["form_id"] == "998877"
    assert data["full_name"] == "Ivan Petrov"
    assert data["email"] == "ivan@example.com"
    assert data["phone"] == "+48504004622"
    assert data["ad_id"] == 1800000000000001


def test_meta_leadgen_payload_is_not_a_tiktok_lead():
    payload = _make_payload(
        [
            {"name": "email", "values": ["a@example.com"]},
        ]
    )
    payload["object"] = "page"
    assert normalizer.tiktok_lead_entry(payload) is None
