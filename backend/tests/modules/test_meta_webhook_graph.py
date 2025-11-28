import pytest

from backend.app.modules.leads import webhook


class DummyDB:
    pass


@pytest.mark.anyio
async def test_enrich_entries_fetches_field_data(monkeypatch):
    event = webhook.MetaWebhookIn(
        object="page",
        entry=[
            webhook.MetaEntry(
                id="PAGE1",
                changes=[
                    webhook.MetaChange(
                        field="leadgen",
                        value=webhook.MetaLeadValue(leadgen_id="LEAD1", page_id="PAGE1"),
                    )
                ],
            )
        ],
    )

    async def fake_token(db, tenant_id, page_id):
        return "token"

    async def fake_fetch(lead_id, token):
        assert lead_id == "LEAD1"
        assert token == "token"
        return {
            "field_data": [
                {"name": "phone", "values": ["+1 (555) 123-4567"]},
                {"name": "full_name", "values": ["Test User"]},
            ],
            "ad_id": "42",
            "form_id": "FORM",
        }

    monkeypatch.setattr(webhook.admin_service, "get_page_access_token", fake_token)
    monkeypatch.setattr(webhook, "_fetch_field_data_from_graph", fake_fetch)
    monkeypatch.setattr(webhook.settings, "pull_field_data_from_graph", True)

    await webhook._enrich_entries_with_graph(DummyDB(), "tenant", event)

    value = event.entry[0].changes[0].value
    assert value.field_data
    assert value.field_data[0].name == "phone"
    assert value.field_data[0].values[0] == "+1 (555) 123-4567"
    assert value.ad_id == "42"
    assert value.form_id == "FORM"
    assert value.graph_error is None


@pytest.mark.anyio
async def test_enrich_entries_skips_when_field_data_present(monkeypatch):
    event = webhook.MetaWebhookIn(
        object="page",
        entry=[
            webhook.MetaEntry(
                id="PAGE1",
                changes=[
                    webhook.MetaChange(
                        field="leadgen",
                        value=webhook.MetaLeadValue(
                            leadgen_id="LEAD1",
                            page_id="PAGE1",
                            field_data=[webhook.MetaField(name="phone", values=["+12345678901"])],
                        ),
                    )
                ],
            )
        ],
    )

    called = False

    async def fake_fetch(*_args, **_kwargs):
        nonlocal called
        called = True
        return {}

    async def token_stub(*args, **kwargs):
        return "token"

    monkeypatch.setattr(webhook.admin_service, "get_page_access_token", token_stub)
    monkeypatch.setattr(webhook, "_fetch_field_data_from_graph", fake_fetch)
    monkeypatch.setattr(webhook.settings, "pull_field_data_from_graph", True)

    await webhook._enrich_entries_with_graph(DummyDB(), "tenant", event)

    assert called is False


@pytest.mark.anyio
async def test_enrich_entries_records_graph_error(monkeypatch):
    event = webhook.MetaWebhookIn(
        object="page",
        entry=[
            webhook.MetaEntry(
                id="PAGE1",
                changes=[
                    webhook.MetaChange(
                        field="leadgen",
                        value=webhook.MetaLeadValue(leadgen_id="LEAD1", page_id="PAGE1"),
                    )
                ],
            )
        ],
    )

    async def fake_token(db, tenant_id, page_id):
        return "token"

    async def fake_fetch(lead_id, token):
        raise webhook.GraphAPIError("190", "Invalid OAuth 2.0 Access Token")

    monkeypatch.setattr(webhook.admin_service, "get_page_access_token", fake_token)
    monkeypatch.setattr(webhook, "_fetch_field_data_from_graph", fake_fetch)
    monkeypatch.setattr(webhook.settings, "pull_field_data_from_graph", True)

    await webhook._enrich_entries_with_graph(DummyDB(), "tenant", event)
    assert event.entry[0].changes[0].value.graph_error == "GRAPH_190"
