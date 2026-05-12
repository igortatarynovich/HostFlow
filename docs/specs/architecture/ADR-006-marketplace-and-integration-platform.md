# ADR-006: Marketplace и Integration Platform (эволюция Integration Hub)

## Status

**Accepted (product & architecture direction).** Имплементация **поэтапная**: текущий код (флаги модулей, `tenant.settings`, отдельные таблицы кредов вроде `meta_lead_credentials`, communications) **не обязан** сразу соответствовать целевой модели ниже; новые интеграции и UI **Marketplace** проектируются с опорой на этот ADR.

## Context

Продукт эволюционирует от образа **«CRM для рекрутинга»** к **модульной платформе операций workforce с экосистемой Marketplace**. Текущий **Integration Hub** нужно переработать в **HostFlow Marketplace** — единую точку обнаружения, установки и настройки возможностей платформы, с явным разделением типов офферов и правил монетизации.

Связанные решения:

- Владение данными и границы tenant/company — [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md).  
- Пять продуктовых модулей и биллинг — [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md).  
- Три уровня настроек (Tenant → Company → Module Settings) — [`ADR-005`](ADR-005-three-level-settings-hierarchy.md).  
- Перечень существующих webhook/API интеграций — [`../integration.md`](../integration.md).  
- Канонические `offer_key` и категории витрины — [`../marketplace-catalog-keys.md`](../marketplace-catalog-keys.md).  
- MVP-модель таблиц — [`marketplace-integrations-data-model.md`](marketplace-integrations-data-model.md).

## Decision: четыре слоя продукта

| Слой | Назначение | Примеры | Монетизация (принцип) |
|------|------------|---------|------------------------|
| **Platform features** | Базовые возможности ядра (UX, безопасность, аудит, базовые каналы как **capabilities**, а не «отдельные продукты») | Аутентификация, роли, tenant/workspace, уведомления; **Basic Forms** (см. [`ADR-007`](ADR-007-forms-platform-capability.md)) | Входит в подписку / базовый план; не дробить на отдельные SKU без причины |
| **Business modules** | Независимые продуктовые модули HostFlow | Recruitment, HR/Kadry, Fleet, Services/Orders, Finance/Billing | **Основной** способ монетизации: отдельно, bundle, addon |
| **Integrations (core)** | Стандартные подключения к внешним системам, повышающие adoption и снижающие friction | WhatsApp, Telegram, Email, Google/Outlook-календари и контакты, Slack, Zoom, Meta Leads, облачные диски (см. §1) | **По умолчанию free / в базовом плане**; не позиционировать как отдельные платные продукты |
| **Marketplace apps / extensions** | Расширения экосистемы (first-party, third-party), узкоспециализированные коннекторы и инструменты | Payroll, TMS, ERP, OCR, AI-инструменты, compliance по странам, VoIP/SMS провайдеры; **коннекторы job boards** (Indeed, Pracuj, …) в связке с [`ADR-008`](ADR-008-job-publishing-and-distribution.md) | Free, paid, rev-share — по модели приложения |

**Правило позиционирования:** *Core integrations* — это **platform capabilities** (communication, synchronization, productivity, adoption), а не линейка «мини-продуктов».

---

## 1. Core integrations (FREE / baseline)

Базовые интеграции, которые **увеличивают adoption**, **уменьшают friction**, **повышают retention**. Их **не следует** агрессивно монетизировать.

**Примеры (не исчерпывающе):**

- Messaging / comms: **WhatsApp**, **Telegram**, **Viber**, **Slack**, **Microsoft Teams**, **Zoom**  
- Email / calendar / contacts: **Email**, **Gmail**, **Outlook**, **Google Calendar**, **Google Contacts**  
- Identity / productivity (где применимо): **Google** (workspace-флоу)  
- Lead capture: **Meta Leads** (и аналоги по политике продукта)  
- Storage / files: **Google Drive**, **Dropbox**, **OneDrive**

**Продуктовое правило (важно):**

- **WhatsApp / Telegram / Gmail / Google-интеграции** и аналогичные каналы — драйверы внедрения; тарификация «за каждый базовый канал» противоречит стратегии платформы.  
- Монетизировать целесообразно: **бизнес-воркфлоу**, **автоматизация**, модули **HR / Fleet / Finance**, **advanced features**, **premium marketplace apps** — а не базовую коммуникацию.

---

## 2. Paid modules (business modules)

Основные продуктовые модули HostFlow (см. ADR-004):

- **Recruitment**  
- **HR / Kadry**  
- **Fleet Management**  
- **Services / Orders**  
- **Finance / Billing**

**Свойства:**

- Независимы в продуктовой логике (вкл/выкл, лицензирование).  
- Могут продаваться **отдельно**, как **addons**, входить в **bundles**.  
- Настройки поведения модуля **per company** — канон ADR-005 (`company_module_settings`, `module_key`).

---

## 3. Marketplace apps / extensions (future-ready)

Архитектура должна допускать **каталог приложений**, не смешивая их с «core integrations» и с пятью модулями.

**Примеры категорий офферов:**

- Payroll, TMS, ERP, accounting  
- AI tools, OCR  
- Compliance (в т.ч. country-specific HR / driver compliance)  
- SMS / VoIP провайдеры  
- Automation (сценарии, RPA-уровень — по решению продукта)

**Модели приложения:**

- Free / paid / third-party / first-party (с политикой доверия, подписи, review — детали вне scope этого ADR).

---

## UI: HostFlow Marketplace (замена Integration Hub)

Целевой UX: единый **HostFlow Marketplace** с разделами (витрина), например:

- Communication  
- Productivity  
- HR  
- Fleet  
- Accounting  
- AI  
- Automation  
- Storage  
- Compliance  

Карточка оффера должна явно указывать **тип**: *core integration* | *module* | *marketplace app*, чтобы не создавать у пользователя ощущение «всё платное».

---

## Рекомендуемая модель данных (целевое состояние)

Отделить **продуктовые модули** от **установленных интеграций** и **marketplace apps**.

### Tenant

| Поле / концепт | Назначение |
|----------------|------------|
| `subscription` | План, лимиты, биллинг (существующие и будущие сущности) |
| `enabled_modules` | Пять продуктовых модулей + согласованные флаги (см. ADR-004, snapshot в коде) |
| `installed_integrations` | Какие **core / standard** интеграции подключены на уровне workspace (tenant-wide install) |
| `installed_marketplace_apps` | Установленные приложения из Marketplace (версии, entitlements) |

### Company

| Поле / концепт | Назначение |
|----------------|------------|
| `enabled_modules` | Пересечение с tenant (`company_allows_module`, ADR-003/004) |
| `enabled_integrations` | Какие из tenant-installed интеграций **активны и настраиваются** для этой company (сценарий: tenant подключил WhatsApp, но только одна компания использует для Recruitment) |
| `module_settings` | ADR-005: `company_module_settings` / `settings_json` per `module_key` |

**Пример (из требований):** tenant подключил **WhatsApp**; компания **Focus Personnel** использует его только в контексте **Recruitment** — это достигается связкой **tenant install** + **company-level enable + routing/policy**, а не дублированием кредов на каждую company без необходимости.

---

## Architecture summary

| Термин | Уровень | Отличие от модуля ADR-004 |
|--------|---------|---------------------------|
| Platform features | Core | Не каталогизируются как «приложения» |
| Business module | Лицензируемый продукт | `recruitment`, `hr`, `fleet`, `services`, `finance` |
| Core integration | Tenant/company enable | Adoption; не отдельные SKU |
| Marketplace app | Каталог, отдельный lifecycle | Версии, провайдер, биллинг приложения |

---

## Consequences

1. Новые интеграции классифицировать по ADR-006 **до** размещения в UI (избежать смешения витрины).  
2. Биллинг: раздельные продуктовые события для **модулей**, **premium apps** и (осторожно) **advanced automation** — не для базовых comms без явного продуктового решения.  
3. Технический долг: постепенно вынести разрозненные креды/флаги в модель **installation** (tenant) и **enablement** (company) с единым каталогом ключей интеграций.  
4. Документ [`integration.md`](../integration.md) остаётся **операционным** справочником по webhook/API; нормативная классификация — этот ADR.

## Long-term positioning

**От:** «CRM for recruitment»  
**К:** **Modular Workforce Operations Platform with Marketplace Ecosystem**

---

## References

- [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md)  
- [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md)  
- [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md)  
- [`ADR-005`](ADR-005-three-level-settings-hierarchy.md)  
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)  
- [`ADR-007-forms-platform-capability.md`](ADR-007-forms-platform-capability.md) — публичные формы как input layer; **Advanced Forms** как платный слой, ортогонально Marketplace apps  
- [`ADR-008-job-publishing-and-distribution.md`](ADR-008-job-publishing-and-distribution.md) — публикация вакансий в Recruitment; внешние порталы как marketplace-интеграции  
- [`ADR-009-document-hub-platform-layer.md`](ADR-009-document-hub-platform-layer.md) — общий слой документов (OCR, e-sign и др. могут приходить как integrations/apps)  
- [`../integration.md`](../integration.md)

## История

- 2026-05: первичная фиксация слоёв (core integrations / paid modules / marketplace apps), целевой модели tenant/company, витрины Marketplace, правил монетизации и позиционирования платформы.
