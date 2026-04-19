"""Per-channel adapter-config builders for the communications package.

Extracted from ``communications/__init__.py`` (Phase 1 god-module split).

Each helper translates the persisted ``CommunicationChannelAccount.settings_json``
into the adapter-config dataclass used by the matching service module
(`communications_email_imap`, `communications_telegram`, etc).

Depends on:
* :mod:`backend.app.api.v1.communications._helpers.utils` — ``_as_dict``
* :mod:`backend.app.core.crypto` — ``decrypt_secret``
* :mod:`backend.app.services.communications_*` — adapter dataclasses
"""

from __future__ import annotations

from backend.app.core.crypto import decrypt_secret
from backend.app.models.communication import CommunicationChannelAccount
from backend.app.services.communications_email_imap import ImapClientConfig
from backend.app.services.communications_meta import MetaGraphConfig
from backend.app.services.communications_telegram import TelegramBotConfig
from backend.app.services.communications_viber import ViberBotConfig
from backend.app.services.communications_whatsapp import WhatsAppCloudConfig

from .utils import _as_dict

__all__ = [
    "_imap_config_from_account_settings",
    "_telegram_config_from_account_settings",
    "_whatsapp_config_from_account_settings",
    "_viber_config_from_account_settings",
    "_messenger_graph_config_from_account_settings",
    "_instagram_graph_config_from_account_settings",
]


def _imap_config_from_account_settings(
    account: CommunicationChannelAccount,
) -> ImapClientConfig | None:
    settings = _as_dict(account.settings_json)
    imap_json = _as_dict(settings.get("imap"))
    host = str(imap_json.get("host") or "").strip()
    user = str(imap_json.get("user") or "").strip()
    if not host or not user:
        return None
    password = ""
    if imap_json.get("password_encrypted"):
        password = decrypt_secret(str(imap_json.get("password_encrypted") or "")) or ""
    elif imap_json.get("password"):
        password = str(imap_json.get("password") or "")
    port = int(imap_json.get("port") or (993 if bool(imap_json.get("use_ssl", True)) else 143))
    return ImapClientConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        use_ssl=bool(imap_json.get("use_ssl", True)),
        folder=str(imap_json.get("folder") or "INBOX"),
        search_criteria=str(imap_json.get("search_criteria") or "UNSEEN"),
        mark_seen=bool(imap_json.get("mark_seen", False)),
        timeout_seconds=max(3, int(imap_json.get("timeout_seconds") or 15)),
    )


def _telegram_config_from_account_settings(
    account: CommunicationChannelAccount,
) -> TelegramBotConfig | None:
    settings = _as_dict(account.settings_json)
    tg_json = _as_dict(settings.get("telegram"))
    token = ""
    if tg_json.get("bot_token_encrypted"):
        token = decrypt_secret(str(tg_json.get("bot_token_encrypted") or "")) or ""
    elif tg_json.get("bot_token"):
        token = str(tg_json.get("bot_token") or "")
    token = token.strip()
    if not token:
        return None
    return TelegramBotConfig(
        bot_token=token,
        timeout_seconds=max(3, int(tg_json.get("timeout_seconds") or 15)),
    )


def _whatsapp_config_from_account_settings(
    account: CommunicationChannelAccount,
) -> WhatsAppCloudConfig | None:
    settings = _as_dict(account.settings_json)
    wa_json = _as_dict(settings.get("whatsapp"))
    access_token = ""
    if wa_json.get("access_token_encrypted"):
        access_token = decrypt_secret(str(wa_json.get("access_token_encrypted") or "")) or ""
    elif wa_json.get("access_token"):
        access_token = str(wa_json.get("access_token") or "")
    phone_number_id = str(
        wa_json.get("phone_number_id") or account.external_account_ref or ""
    ).strip()
    api_version = str(wa_json.get("api_version") or "v20.0").strip() or "v20.0"
    access_token = access_token.strip()
    if not access_token or not phone_number_id:
        return None
    return WhatsAppCloudConfig(
        access_token=access_token,
        phone_number_id=phone_number_id,
        api_version=api_version,
        timeout_seconds=max(3, int(wa_json.get("timeout_seconds") or 15)),
    )


def _viber_config_from_account_settings(
    account: CommunicationChannelAccount,
) -> ViberBotConfig | None:
    settings = _as_dict(account.settings_json)
    viber_json = _as_dict(settings.get("viber"))
    token = ""
    if viber_json.get("bot_token_encrypted"):
        token = decrypt_secret(str(viber_json.get("bot_token_encrypted") or "")) or ""
    elif viber_json.get("bot_token"):
        token = str(viber_json.get("bot_token") or "")
    token = token.strip()
    if not token:
        return None
    return ViberBotConfig(
        bot_token=token,
        timeout_seconds=max(3, int(viber_json.get("timeout_seconds") or 15)),
    )


def _messenger_graph_config_from_account_settings(
    account: CommunicationChannelAccount,
) -> tuple[MetaGraphConfig | None, str]:
    settings = _as_dict(account.settings_json)
    messenger_json = _as_dict(settings.get("messenger"))
    access_token = ""
    if messenger_json.get("access_token_encrypted"):
        access_token = (
            decrypt_secret(str(messenger_json.get("access_token_encrypted") or "")) or ""
        )
    elif messenger_json.get("access_token"):
        access_token = str(messenger_json.get("access_token") or "")
    access_token = access_token.strip()
    page_id = str(messenger_json.get("page_id") or account.external_account_ref or "").strip()
    api_version = str(messenger_json.get("api_version") or "v20.0").strip() or "v20.0"
    if not access_token or not page_id:
        return None, page_id
    return (
        MetaGraphConfig(
            access_token=access_token,
            api_version=api_version,
            timeout_seconds=max(3, int(messenger_json.get("timeout_seconds") or 15)),
        ),
        page_id,
    )


def _instagram_graph_config_from_account_settings(
    account: CommunicationChannelAccount,
) -> tuple[MetaGraphConfig | None, str]:
    settings = _as_dict(account.settings_json)
    instagram_json = _as_dict(settings.get("instagram"))
    access_token = ""
    if instagram_json.get("access_token_encrypted"):
        access_token = (
            decrypt_secret(str(instagram_json.get("access_token_encrypted") or "")) or ""
        )
    elif instagram_json.get("access_token"):
        access_token = str(instagram_json.get("access_token") or "")
    access_token = access_token.strip()
    account_id = str(
        instagram_json.get("account_id") or account.external_account_ref or ""
    ).strip()
    api_version = str(instagram_json.get("api_version") or "v20.0").strip() or "v20.0"
    if not access_token or not account_id:
        return None, account_id
    return (
        MetaGraphConfig(
            access_token=access_token,
            api_version=api_version,
            timeout_seconds=max(3, int(instagram_json.get("timeout_seconds") or 15)),
        ),
        account_id,
    )
