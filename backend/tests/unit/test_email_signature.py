"""Unit tests for canonical outgoing email signature."""

from backend.app.services.email_signature import (
    OutgoingSignature,
    _resolve_logo_url,
    absolute_public_url,
    append_outgoing_signature,
    closing_for_locale,
    default_brand_logo_url,
    merge_signature_block,
    normalize_signature_block,
)


def test_normalize_signature_block_defaults_and_trims() -> None:
    normalized = normalize_signature_block(
        {
            "first_name": " Igor ",
            "last_name": "Tatarynovich",
            "show_phone": False,
            "website": " hostflow.cc ",
        }
    )
    assert normalized["first_name"] == "Igor"
    assert normalized["last_name"] == "Tatarynovich"
    assert normalized["website"] == "hostflow.cc"
    assert normalized["show_phone"] is False
    assert normalized["show_email"] is True
    assert normalized["show_website"] is True


def test_merge_signature_block_patches_fields() -> None:
    merged = merge_signature_block(
        {"first_name": "Igor", "company": "HostFlow", "show_email": True},
        {"company": "Focus Personnel", "show_email": False, "phone": " +48 600 "},
    )
    assert merged["first_name"] == "Igor"
    assert merged["company"] == "Focus Personnel"
    assert merged["phone"] == "+48 600"
    assert merged["show_email"] is False


def test_closing_for_locale() -> None:
    assert closing_for_locale("pl-PL") == "Z poważaniem,"
    assert closing_for_locale("en") == "Kind regards,"
    assert closing_for_locale("ru-RU") == "С уважением,"
    assert closing_for_locale(None) == "Z poważaniem,"


def test_plain_text_signature_omits_logo_url() -> None:
    sig = OutgoingSignature(
        closing="Z poważaniem,",
        full_name="Igor Tatarynovich",
        position="Founder & CEO",
        company="HostFlow",
        phone="+48 504 004 622",
        email="info@hostflow.cc",
        website="https://hostflow.cc",
        website_display="hostflow.cc",
        logo_url="https://hostflow.cc/logo_hf.svg",
        show_phone=True,
        show_email=True,
        show_website=True,
    )
    text = sig.plain_text()
    assert text.startswith("Z poważaniem,")
    assert "☎ +48 504 004 622" in text
    assert "✉ info@hostflow.cc" in text
    assert "↗ hostflow.cc" in text
    assert "logo_hf.svg" not in text
    assert "https://" not in text
    assert text.endswith("↗ hostflow.cc")


def test_html_signature_uses_brand_color_and_constrained_logo() -> None:
    from backend.app.services.email_signature import BRAND_COLOR, LOGO_WIDTH_PX

    sig = OutgoingSignature(
        closing="Z poważaniem,",
        full_name="Igor Tatarynovich",
        position="Founder & CEO",
        company="HostFlow",
        phone="+48504004622",
        email="info@hostflow.cc",
        website="https://hostflow.cc",
        website_display="hostflow.cc",
        logo_url="https://hostflow.cc/logo_hf.svg",
        show_phone=True,
        show_email=True,
        show_website=False,
    )
    rendered = sig.html()
    assert f"color:{BRAND_COLOR}" in rendered
    assert "<strong" in rendered and "Igor Tatarynovich" in rendered
    assert "HostFlow" in rendered
    assert "☎" in rendered and "✉" in rendered
    assert f'width="{LOGO_WIDTH_PX}"' in rendered
    assert f"max-width:{LOGO_WIDTH_PX}px" in rendered
    assert "logo_hf.svg" in rendered
    assert "🌐" not in rendered


def test_absolute_public_url_and_default_brand_logo() -> None:
    assert absolute_public_url("/logo_hf.svg") == "https://hostflow.cc/logo_hf.svg"
    assert absolute_public_url("https://cdn.example/logo.png") == "https://cdn.example/logo.png"
    assert default_brand_logo_url().endswith("/logo_hf.svg")
    assert _resolve_logo_url(signature={}, profile={}) == default_brand_logo_url()


def test_append_outgoing_signature_idempotent() -> None:
    from backend.app.services.email_signature import append_outgoing_signature_html, plain_body_to_html

    body = "Po otrzymaniu odpowiedzi skontaktujemy się z Państwem w sprawie dalszych kroków."
    sig = "Z poważaniem,\n\nIgor Tatarynovich"
    once = append_outgoing_signature(body, sig)
    twice = append_outgoing_signature(once, sig)
    assert once == f"{body}\n\n{sig}"
    assert twice == once

    html_sig = "<div>SIG</div>"
    html_once = append_outgoing_signature_html(plain_body_to_html(body), html_sig)
    assert "SIG" in html_once
    assert "<br>" in html_once
    html_twice = append_outgoing_signature_html(html_once, html_sig)
    assert html_twice.count("SIG") == 1
