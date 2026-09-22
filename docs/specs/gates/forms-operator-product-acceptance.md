# Forms Operator Product Acceptance

**Status:** **OPEN**  
**Measured:** 2026-09-22, tree `/opt/HostFlow`  
**Contract:** [Forms Operator Product Contract](../architecture/forms-operator-product-contract.md)  
**Does not reopen:** [`forms.public_contract.v1`](../architecture/forms-public-contract.md), Field Catalog v1, C1–C6 Foundation, Mapping Authority program  
**Does not schedule:** [FP-1…FP-5](../tasks/external-intake-forms-publish.md)

---

## Verdict

Оператор без подготовки **не** проходит путь «создал → настроил → опубликовал snapshot → отдал ссылку или embed → принял ответ → увидел, куда он записался».

Замер: **0 PASS, 8 PARTIAL, 7 GAP, 1 OPEN** из F-01…F-16. Итог gate — **OPEN**.

Публикация, которую требует контракт, в коде есть и в продукт не выведена. `commit_publish` в `backend/app/forms_platform/adapter.py` дописывает `FormPublicationVersion`. Вызовов `commit_publish` из HTTP-маршрутов нет. Строки `forms_publish.v1` в репозитории нет: authority публикации — операция `publish` контракта `forms.public_contract.v1`. Кнопка «Save and activate» и флаг активности — не эта операция. Builder прямо говорит, что publish — отдельное действие и P3 locked (`hostflow-frontend/src/pages/admin/FormsBuilderPage.tsx`).

Публичный URL `/public/intake?lead_form_slug=…` копируется из списка форм. Его отдаёт presentation intake, а не экран, который показывает оператору номер `FormPublicationVersion` и embed того же snapshot. FP-5 в каноне по-прежнему **QUEUED**, не PASS. Поэтому hosted URL и чужой submit не закрывают F-07 и F-09.

---

## Как читать вердикт

| Вердикт | Значение |
|---------|----------|
| **PASS** | Оператор делает это на продуктовом пути, и путь совпадает с контрактом |
| **PARTIAL** | Смежный механизм есть; критерий оператора не выполнен |
| **GAP** | На пути оператора этого нет |
| **OPEN** | Сквозной приёмки не было |

---

## Matrix

| ID | Requirement | Expected operator behavior | Current implementation | Verdict |
|----|-------------|----------------------------|------------------------|---------|
| F-01 | Create form | Создать форму без разработчика: название, описание, язык, бизнес-тип, компания; с нуля или из шаблона | Мастер на `/app/settings/lead-forms` и `/app/marketing/forms` (`LeadFormsSettingsPage`): «Create form», тип «Candidate application» / «Company request» и др., название, язык PL/EN/RU, public slug. Описания, компании и галереи шаблонов нет. Карточка `IntakeFormDetailPage` показывает **Intake Source profile**, **Route intent**, Entity Profile, `qualified_code` | **PARTIAL** |
| F-02 | Draft autosave | Уход со страницы не теряет работу | «Save draft» вручную, бейдж Unsaved / Saved, конфликт ревизии с «Reload server draft». Автосохранения нет | **PARTIAL** |
| F-03 | Add / reorder fields | Визуальный конструктор: добавить, удалить, дублировать, перетащить, подписи, проверка, условия, ширина, структура | Палитра, удаление, стрелки вверх/вниз, label / help / placeholder / required через config каталога. Нет duplicate, drag-and-drop, ширины, условной логики в Builder, preview и структурных блоков | **PARTIAL** |
| F-04 | Mapping | Визуально: ответ → понятное поле HostFlow, без второго словаря | Редактор — `/app/marketing/sources/:sourceId/mapping`, не карточка формы. `IntakeFormMappingEditor` только ведёт туда или пишет, что источник не привязан. В списке назначения виден `label`; в правило пишется код. Нет блокировки Publish по несовместимости, дублю и обязательности | **PARTIAL** |
| F-05 | Preview | Desktop, mobile и тест без боевой сущности | На карточке — таблица сохранённых вопросов. Smoke test (`POST …/smoke-test`) создаёт Lead draft: «no Candidate row was inserted», Lead при этом создаётся. Отдельного test mode нет | **GAP** |
| F-06 | Publish | Одно действие, проверка готовности, Live и версия | `commit_publish` не вызывается из продукта. Активация формы и bump presentation — другие операции. История версий в UI форм нет | **GAP** |
| F-07 | Hosted URL | Скопировать ссылку, которая открывает опубликованный snapshot | Copy URL есть: `/public/intake?lead_form_slug=…`. Это не выдача текущего `FormPublicationVersion` с экрана Publish | **PARTIAL** |
| F-08 | Embed | Скопировать iframe / snippet того же snapshot | В UI форм embed нет | **GAP** |
| F-09 | Submission | Посторонний человек отправляет боевую опубликованную форму | Публичный intake принимает ответы и может создать intake-запись. Привязки к версии, которую оператор зафиксировал через `commit_publish`, на этом пути нет. Канон FP-5 не PASS | **PARTIAL** |
| F-10 | Responses | Forms → Form → Responses: кто, когда, версия, сырые ответы, куда записалось | Списка ответов на карточке формы нет. Ближайший экран — `/app/marketing/diagnostics` (JSON маршрута и payload), плюс ответы на карточке лида | **GAP** |
| F-11 | Edit live form | Edit меняет draft, live остаётся прежним | Разделения «live snapshot / новый draft» в UI нет, потому что live для оператора — не publication version | **GAP** |
| F-12 | Republish / versioning | V2 не портит ответы V1; откат — новая версия с содержимым старой | Ledger append-only есть в адаптере. Оператор не публикует V2 и не откатывает версию | **GAP** |
| F-13 | Branding | Тема компании наследуется, форма переопределяет нужное | `forms.feature_flags.themes_advanced` по умолчанию выключен. Модели темы формы и экрана бренда нет. P4 в каноне locked | **GAP** |
| F-14 | GDPR | Версионированный текст согласия, время, версия формы; старые ответы не переписываются | `consent_pin` (`terms_version`, `privacy_version`) пишется внутри `commit_publish`. Публичные чекбоксы privacy / RODO / terms ведут на фиксированные `/legal/*.html`. Экрана, где оператор задаёт текст и видит evidence по ответу, нет | **PARTIAL** |
| F-15 | Failure handling | Сбой не теряет submission; оператор видит Received — Action required | Коды runtime (`forms_endpoint_inactive`, validation, routing unresolved) и диагностика есть. На форме нет статуса «ответ получен, нужно действие». Несозданный кандидат не объясняется в Forms | **PARTIAL** |
| F-16 | No-code E2E | Новый оператор проходит весь критерий контракта | Сквозной прогон не выполнялся и на текущем UI не сходится | **OPEN** |

---

## Каталог типов

Stdlib (`forms.field_catalog.stdlib.v1`, `backend/app/forms_platform/field_catalog/stdlib.py`): 12 компонентов.

| Тип контракта | В каталоге | Вердикт относительно контракта |
|---------------|------------|--------------------------------|
| Короткий текст, длинный текст, число | `text`, `textarea`, `number` | Компонент есть. Правила пустого ответа и маппинг на форме не доведены до оператора |
| Email, телефон, дата | `email`, `phone`, `date` | Компонент есть. Отдельной продуктовой гарантии нормализации телефона и дат на операторском пути нет |
| Один / несколько / радио / чекбокс | `select`, `multiselect`, `radio`, `checkbox` | Компонент есть. Редактор вариантов — общее текстовое поле config, не option mapping |
| Файл | `file` | Компонент есть. Сбой загрузки не выведен в Responses |
| Скрытое | `hidden` | Компонент есть (`default_value`) |
| Дата и время, да/нет, адрес, URL | нет отдельных id | **GAP** |
| Страна | нет; страна живёт в presentation профиля, не в stdlib | **GAP** как тип конструктора со справочником |
| Согласие | нет `forms.field.consent` | **GAP** как контракт evidence; pin версии terms/privacy есть только внутри `commit_publish` |
| Заголовок, абзац, разделитель, секция, изображение | нет | **GAP**. Положительный факт: layout-назначений для маппинга эти отсутствующие блоки не создают |

---

## Что уже есть и этот gate не переоткрывает

- Draft Builder сохраняется отдельно от публикации (C3): save не вызывает `commit_publish`.
- `FormPublicationVersion` неизменяем; новая публикация — новая строка.
- Runtime отвергает authoring payload (`forms_runtime_not_publication`).
- Field Catalog v1 заморожен; Builder не имеет права объявлять свои типы.
- Mapping Authority остаётся владельцем canonical destination. Текущий разрыв F-04 — в том, что оператор не настраивает это на форме понятными именами, а не в отсутствии реестра.

---

## Когда gate может стать PASS

Все F-01…F-15 — **PASS**, и отдельный прогон F-16 фиксирует, что человек без знания HostFlow проходит критерий контракта на чистом тенанте: branded form, поля, визуальный маппинг, preview без боевой сущности, Publish через `commit_publish`, hosted URL **или** embed того же snapshot, реальный ответ, исходные ответы и созданная или явно остановленная бизнес-запись.

PARTIAL не суммируется в PASS. Закрытие FP-5 само по себе не закрывает этот gate: FP не включает embed, бренд, Responses, consent UI и откат версии.

---

## Evidence (где смотрели)

- `backend/app/forms_platform/adapter.py` — `commit_publish`
- `backend/app/forms_platform/field_catalog/stdlib.py` — `STANDARD_COMPONENT_IDS`
- `backend/app/services/intake_form_admin_context.py` — `run_intake_form_smoke_test`
- `hostflow-frontend/src/pages/admin/LeadFormsSettingsPage.tsx`
- `hostflow-frontend/src/pages/admin/IntakeFormDetailPage.tsx`
- `hostflow-frontend/src/pages/admin/FormsBuilderPage.tsx`
- `hostflow-frontend/src/components/admin/IntakeFormMappingEditor.tsx`
- Поиск по репозиторию: `forms_publish` — нет совпадений; `commit_publish(` вне определения адаптера и тестов — нет
