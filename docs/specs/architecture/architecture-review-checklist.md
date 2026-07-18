# Architecture Review Checklist (P-01…P-05)

**Status:** canonical  
**Rules:** [`ADR-025`](ADR-025-standard-adapter-boundary.md) · [`ADR-026`](ADR-026-capability-ownership.md) · [`ADR-027`](ADR-027-capability-composition.md) · [`ADR-028`](ADR-028-configuration-ownership.md) · [`ADR-029`](ADR-029-settings-contract.md)  
**Catalog:** [`platform-capability-catalog.md`](platform-capability-catalog.md)  
**Settings Manifest:** [`capability-settings-manifest.md`](capability-settings-manifest.md)  

---

## Шесть главных вопросов

| # | Вопрос | Правило |
|---|--------|---------|
| 1 | Только канонические Standard Adapters? | **P-01** / Exposes |
| 2 | Только к владельцам capabilities? | **P-02** / Owns |
| 3 | Композиция, а не дубликат? | **P-03** / Consumes |
| 4 | Не чужой Forbidden? | **Boundary** |
| 5 | Knobs только у configuration owner? | **P-04** / Configures |
| 6 | Settings опубликованы через **Settings Manifest** владельца (не свалка UI)? | **P-05** |

---

## P-01 — Exposes

- [ ] Нет прямого импорта / SQL / ORM / provider SDK из Business  
- [ ] Доступ только через **Exposes** владельца  

## P-02 / Boundary — Owns + Forbidden

- [ ] Kind (Infrastructure / Platform / Business) указан  
- [ ] Изменение в **Owns**; не в **Forbidden**  
- [ ] Business не владеет Infrastructure/Platform stacks  

## P-03 — Consumes

- [ ] Compose через Consumes; новый capability = ADR + Passport + Manifest **до** кода  

## P-04 — Configures (ownership)

- [ ] Каждый knob принадлежит ровно одной capability  
- [ ] Нет SMTP / OCR / LLM / Meta App SoT в Business settings  

## P-05 — Settings Contract (publication)

- [ ] Новый/изменённый knob отражён в **Settings Manifest** владельца (key, type, default, license, restart/migration, section)  
- [ ] Admin UI — **capability space**, не техническая свалка («General → SMTP» как SoT IA)  
- [ ] Лицензия / disable capability исключает Manifest из shell  
- [ ] Export/import/backup затрагивает только Manifest keys  
- [ ] Passport не раздут полным списком knobs (pointer → Manifest)  

## Intake / Endpoint

- [ ] Spine Endpoint → Submission → Routing → Decision → Business Entity  

## Документация

- [ ] Catalog Passport + Manifest schema обновлены в том же PR  

---

## История

- 2026-07-18: P-01…P-04 + Boundary.  
- 2026-07-18: P-05 Settings Contract / Manifest / capability-scoped admin IA.
