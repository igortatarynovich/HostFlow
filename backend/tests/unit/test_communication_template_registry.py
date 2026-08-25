"""Unit tests for questionnaire invite email templates."""

from backend.app.services.communication_templates import render_template, resolve_template


def test_questionnaire_invite_email_templates_pl_en_ru() -> None:
    tpl = resolve_template("questionnaire_invite_email_v1")
    assert "manager_name" not in tpl.allowed_variables
    assert "company_name" not in tpl.allowed_variables
    vars_ = {
        "contact_name": "Anna",
        "questionnaire_url": "https://hostflow.cc/public/apply/tok?lang=pl",
    }
    pl = render_template(tpl, locale="pl", variables=vars_)
    assert pl["subject"] == "Kilka pytań dotyczących współpracy"
    assert "https://hostflow.cc/public/apply/tok?lang=pl" in pl["body"]
    assert "{{" not in pl["body"]
    assert "Z poważaniem" not in pl["body"]
    assert pl["body"].endswith(
        "Po otrzymaniu odpowiedzi skontaktujemy się z Państwem w sprawie dalszych kroków."
    )

    en = render_template(tpl, locale="en", variables={**vars_, "questionnaire_url": "https://x/?lang=en"})
    assert en["subject"] == "A few questions about your request"
    assert "Kind regards" not in en["body"]

    ru = render_template(tpl, locale="ru", variables={**vars_, "questionnaire_url": "https://x/?lang=ru"})
    assert ru["subject"] == "Несколько вопросов по вашему обращению"
    assert "С уважением" not in ru["body"]
