"""Internal helper sub-package for ``backend.app.api.v1.communications``.

These modules host helpers that used to live in the monolithic
``communications.py`` god-module. They are organised by responsibility:

* :mod:`utils` — pure stdlib utilities (``_now_utc``, ``_as_dict`` …).
* :mod:`working_hours` — working-hours / time-off date math.
* :mod:`account_settings` — account JSON sanitisation, encryption,
  serialisation to ``CommunicationChannelAccountOut``.
* :mod:`oauth` — OAuth token storage, refresh, mailbox access.
* :mod:`channels` — per-channel config builders (telegram, whatsapp,
  viber, meta graph, imap).

External callers MUST import only via the public package surface
(``from backend.app.api.v1.communications import …``) — the ``_helpers``
prefix is private and may be reorganised further.
"""
