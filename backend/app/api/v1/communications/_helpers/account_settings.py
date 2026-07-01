"""Account-settings serialisation/encryption for the communications package.

Extracted from ``communications/__init__.py`` (Phase 1 god-module split).

Depends on:
* :mod:`backend.app.api.v1.communications._helpers.utils`
* :mod:`backend.app.api.v1.communications.schemas` (output Pydantic model)
* :mod:`backend.app.core.crypto` (``encrypt_secret``)
* :mod:`backend.app.models.communication` (``CommunicationChannelAccount``)
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from backend.app.core.crypto import encrypt_secret
from backend.app.models.communication import CommunicationChannelAccount

from ..schemas import CommunicationChannelAccountOut
from .utils import _as_dict

__all__ = [
    "_derive_account_status",
    "_sanitize_account_settings_for_out",
    "_account_out",
    "_normalize_account_settings_for_store",
]


def _derive_account_status(account: CommunicationChannelAccount) -> Tuple[str, str | None]:
    settings = _as_dict(account.settings_json)
    sync = _as_dict(settings.get("sync"))
    connection = _as_dict(settings.get("connection"))
    if not bool(account.is_active):
        return "disabled", "Account disabled"
    if str(connection.get("status") or "") == "error":
        return "error", str(connection.get("last_error") or "Connection error")
    if str(sync.get("status") or "") == "error":
        return "error", str(sync.get("last_error") or "Sync error")
    if connection.get("last_test_at"):
        return "connected", None
    return "not_tested", "Connection was not tested yet"


def _sanitize_account_settings_for_out(settings_json: Any) -> Dict[str, Any]:
    settings = _as_dict(settings_json)
    out = {**settings}
    imap_cfg = _as_dict(out.get("imap"))
    if imap_cfg:
        imap_out = {**imap_cfg}
        if "password" in imap_out:
            imap_out.pop("password", None)
        imap_out["has_password"] = bool(imap_cfg.get("password_encrypted") or imap_cfg.get("password"))
        out["imap"] = imap_out
    telegram_cfg = _as_dict(out.get("telegram"))
    if telegram_cfg:
        tg_out = {**telegram_cfg}
        tg_out.pop("bot_token", None)
        tg_out["has_bot_token"] = bool(telegram_cfg.get("bot_token_encrypted") or telegram_cfg.get("bot_token"))
        out["telegram"] = tg_out
    whatsapp_cfg = _as_dict(out.get("whatsapp"))
    if whatsapp_cfg:
        wa_out = {**whatsapp_cfg}
        wa_out.pop("access_token", None)
        wa_out["has_access_token"] = bool(whatsapp_cfg.get("access_token_encrypted") or whatsapp_cfg.get("access_token"))
        out["whatsapp"] = wa_out
    viber_cfg = _as_dict(out.get("viber"))
    if viber_cfg:
        viber_out = {**viber_cfg}
        viber_out.pop("bot_token", None)
        viber_out["has_bot_token"] = bool(viber_cfg.get("bot_token_encrypted") or viber_cfg.get("bot_token"))
        out["viber"] = viber_out
    messenger_cfg = _as_dict(out.get("messenger"))
    if messenger_cfg:
        messenger_out = {**messenger_cfg}
        messenger_out.pop("access_token", None)
        messenger_out.pop("app_secret", None)
        messenger_out["has_access_token"] = bool(
            messenger_cfg.get("access_token_encrypted") or messenger_cfg.get("access_token")
        )
        messenger_out["has_app_secret"] = bool(
            messenger_cfg.get("app_secret_encrypted") or messenger_cfg.get("app_secret")
        )
        out["messenger"] = messenger_out
    instagram_cfg = _as_dict(out.get("instagram"))
    if instagram_cfg:
        instagram_out = {**instagram_cfg}
        instagram_out.pop("access_token", None)
        instagram_out["has_access_token"] = bool(
            instagram_cfg.get("access_token_encrypted") or instagram_cfg.get("access_token")
        )
        out["instagram"] = instagram_out
    oauth_cfg = _as_dict(out.get("oauth"))
    if oauth_cfg:
        oauth_out = {**oauth_cfg}
        oauth_out.pop("access_token", None)
        oauth_out.pop("refresh_token", None)
        oauth_out.pop("id_token", None)
        oauth_out.pop("client_secret", None)
        oauth_out["has_access_token"] = bool(
            oauth_cfg.get("access_token_encrypted") or oauth_cfg.get("access_token")
        )
        oauth_out["has_refresh_token"] = bool(
            oauth_cfg.get("refresh_token_encrypted") or oauth_cfg.get("refresh_token")
        )
        oauth_out["has_id_token"] = bool(
            oauth_cfg.get("id_token_encrypted") or oauth_cfg.get("id_token")
        )
        oauth_out["has_client_secret"] = bool(
            oauth_cfg.get("client_secret_encrypted") or oauth_cfg.get("client_secret")
        )
        out["oauth"] = oauth_out
    return out


def _account_out(account: CommunicationChannelAccount) -> CommunicationChannelAccountOut:
    return CommunicationChannelAccountOut(
        id=str(account.id),
        channel=account.channel,
        account_label=account.account_label,
        external_account_ref=account.external_account_ref,
        inbox_address=account.inbox_address,
        is_active=bool(account.is_active),
        settings_json=_sanitize_account_settings_for_out(account.settings_json),
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def _normalize_account_settings_for_store(settings_json: Any) -> Dict[str, Any]:
    settings = _as_dict(settings_json)
    out = {**settings}
    imap_cfg = _as_dict(out.get("imap"))
    if imap_cfg:
        imap_mut = {**imap_cfg}
        raw_password = imap_mut.pop("password", None)
        if raw_password is not None:
            raw_password_text = str(raw_password).strip()
            if raw_password_text:
                imap_mut["password_encrypted"] = encrypt_secret(raw_password_text)
        out["imap"] = imap_mut
    telegram_cfg = _as_dict(out.get("telegram"))
    if telegram_cfg:
        tg_mut = {**telegram_cfg}
        raw_token = tg_mut.pop("bot_token", None)
        if raw_token is not None:
            raw_token_text = str(raw_token).strip()
            if raw_token_text:
                tg_mut["bot_token_encrypted"] = encrypt_secret(raw_token_text)
        out["telegram"] = tg_mut
    whatsapp_cfg = _as_dict(out.get("whatsapp"))
    if whatsapp_cfg:
        wa_mut = {**whatsapp_cfg}
        raw_access = wa_mut.pop("access_token", None)
        if raw_access is not None:
            raw_access_text = str(raw_access).strip()
            if raw_access_text:
                wa_mut["access_token_encrypted"] = encrypt_secret(raw_access_text)
        out["whatsapp"] = wa_mut
    viber_cfg = _as_dict(out.get("viber"))
    if viber_cfg:
        viber_mut = {**viber_cfg}
        raw_token = viber_mut.pop("bot_token", None)
        if raw_token is not None:
            raw_token_text = str(raw_token).strip()
            if raw_token_text:
                viber_mut["bot_token_encrypted"] = encrypt_secret(raw_token_text)
        out["viber"] = viber_mut
    messenger_cfg = _as_dict(out.get("messenger"))
    if messenger_cfg:
        messenger_mut = {**messenger_cfg}
        raw_access = messenger_mut.pop("access_token", None)
        raw_secret = messenger_mut.pop("app_secret", None)
        if raw_access is not None:
            raw_access_text = str(raw_access).strip()
            if raw_access_text:
                messenger_mut["access_token_encrypted"] = encrypt_secret(raw_access_text)
        if raw_secret is not None:
            raw_secret_text = str(raw_secret).strip()
            if raw_secret_text:
                messenger_mut["app_secret_encrypted"] = encrypt_secret(raw_secret_text)
        out["messenger"] = messenger_mut
    instagram_cfg = _as_dict(out.get("instagram"))
    if instagram_cfg:
        instagram_mut = {**instagram_cfg}
        raw_access = instagram_mut.pop("access_token", None)
        if raw_access is not None:
            raw_access_text = str(raw_access).strip()
            if raw_access_text:
                instagram_mut["access_token_encrypted"] = encrypt_secret(raw_access_text)
        out["instagram"] = instagram_mut
    oauth_cfg = _as_dict(out.get("oauth"))
    if oauth_cfg:
        oauth_mut = {**oauth_cfg}
        raw_access = oauth_mut.pop("access_token", None)
        raw_refresh = oauth_mut.pop("refresh_token", None)
        raw_id = oauth_mut.pop("id_token", None)
        raw_client_secret = oauth_mut.pop("client_secret", None)
        if raw_access is not None:
            raw_access_text = str(raw_access).strip()
            if raw_access_text:
                oauth_mut["access_token_encrypted"] = encrypt_secret(raw_access_text)
        if raw_refresh is not None:
            raw_refresh_text = str(raw_refresh).strip()
            if raw_refresh_text:
                oauth_mut["refresh_token_encrypted"] = encrypt_secret(raw_refresh_text)
        if raw_id is not None:
            raw_id_text = str(raw_id).strip()
            if raw_id_text:
                oauth_mut["id_token_encrypted"] = encrypt_secret(raw_id_text)
        if raw_client_secret is not None:
            raw_client_secret_text = str(raw_client_secret).strip()
            if raw_client_secret_text:
                oauth_mut["client_secret_encrypted"] = encrypt_secret(raw_client_secret_text)
        out["oauth"] = oauth_mut
    return out
