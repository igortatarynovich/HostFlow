# CRM Production Readiness SSOT (Single Source of Truth)

Дата создания: 2026-03-11  
Последнее обновление: 2026-03-12  
Статус: `IN_PROGRESS`  
Цель: довести продукт до состояния, когда новый клиент проходит путь `Landing -> Signup -> Payment -> Active usage` без участия поддержки.

---

## 1. Как использовать этот файл

Это единственный рабочий документ готовности к запуску продаж CRM.

Правила ведения:
- Любая новая продуктовая/техническая задача, влияющая на продажи и активацию CRM, сначала фиксируется здесь.
- Любая завершенная задача получает: статус, дату, ссылку на PR/коммит/эндпоинт/экран.
- Статусы только из списка: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`.
- Если статус `BLOCKED`, обязательно указывать блокер и владельца решения.
- Git-правило: если в задаче затронуто более `10` файлов, делаем отдельный commit в конце пакета изменений.
- Git-правило: если новая задача логически отличается от текущей, перед началом работ создается новая ветка.
- Git-правило: каждый commit должен отражать логически завершенную задачу/правку и не смешивать несвязанные изменения.
- Git-правило для `F8`: весь `F8` считается одной логической задачей (единый рабочий трек), без дробления на отдельные логические ветки на каждый подшаг.
- Git-правило для `F8`: изменения выполняются пакетами (обычно `3-8` файлов), с одним commit на пакет и понятным тематическим сообщением.
- Git-правило для `F8`: проверка сборкой выполняется один раз на пакет, а не после каждой мелкой правки.
- Git-правило для `F8`: после полного закрытия `F8` выполняется cleanup локальных промежуточных веток, чтобы рабочее дерево оставалось чистым и читаемым.

Легенда:
- `DONE` = принято по критерию + есть проверка (ручная или автотест).
- `IN_PROGRESS` = реализация идет, но критерий не закрыт.
- `BLOCKED` = есть внешний блокер (доступы, провайдер, данные, договоренности).
- `NOT_STARTED` = работа еще не начата.

---

## 2. Источники, консолидированные в этот SSOT

- `docs/crm-e2e-test-report.md`
- `docs/communications-program-status.md`
- `docs/communications-test-matrix.md`
- `docs/CLIENT_AND_ONBOARDING_REDESIGN_PLAN.md`
- `docs/specs/architecture/client_and_subscription_model.md`
- `docs/specs/modules/onboarding.md`
- `docs/specs/modules/payments.md`
- `docs/specs/modules/auth.md`
- `docs/specs/modules/companies.md`
- `docs/specs/modules/leads.md`
- `docs/specs/modules/candidates.md`
- `docs/specs/modules/tenants.md`

## 2.1 Матрица покрытия требований по источникам

| Источник | Статус покрытия в SSOT | Комментарий |
|---|---|---|
| `docs/crm-e2e-test-report.md` | `FULL` | 20 критериев, путь E2E и блокеры перенесены |
| `docs/communications-program-status.md` | `PARTIAL` | Ключевые блоки учтены, но часть domain-detail пока агрегирована |
| `docs/communications-test-matrix.md` | `FULL` | Прямо включено задачей `C1` |
| `docs/CLIENT_AND_ONBOARDING_REDESIGN_PLAN.md` | `PARTIAL` | Основная логика учтена, но сценарии Citronex/POLTRAK требуют явных release-задач |
| `docs/specs/architecture/client_and_subscription_model.md` | `FULL` | Учтено в разделе customer journey и billing path |
| `docs/specs/modules/onboarding.md` | `FULL` | Учтено в фазе B + release gate |
| `docs/specs/modules/payments.md` | `FULL` | Учтено в фазе A (Stripe + webhooks + billing lifecycle) |
| `docs/specs/modules/auth.md` | `PARTIAL` | Self-signup/invite/roles учтены, но не выделено отдельной задачей по auth hardening |
| `docs/specs/modules/companies.md` | `FULL` | Базовый workflow создания и работы с компаниями включен |
| `docs/specs/modules/leads.md` | `FULL` | Включено в фазу C (source -> routing -> action) |
| `docs/specs/modules/candidates.md` | `FULL` | Базовый first-value путь и core operation включены |
| `docs/specs/modules/tenants.md` | `PARTIAL` | Лицензии/лимиты учтены, но нужно отдельно зафиксировать tenant-link сценарии |

## 2.2 Что добавлено после сверки (чтобы закрыть пробелы)

- Добавить release-задачи на `Citronex/POLTRAK` сценарии (tenant link + portal link + visibility scope).
- Добавить отдельную задачу на `Auth hardening` (signup/invite/session recovery) как часть безподдержочного запуска.
- Добавить domain-checklist для communications depth: scheduler, OAuth adapters, provider webhooks, queue/audit consistency.

---

## 3. Definition of Done (20 критериев готовности)

## 3.1 Таблица статусов

| # | Критерий | Статус | Проверка готовности | Комментарий |
|---|---|---|---|---|
| 1 | Полный customer journey без тупиков | `IN_PROGRESS` | Новый пользователь проходит полный путь без ручной помощи | Остался production Stripe + финальный сквозной smoke |
| 2 | Автонастройка под тип компании | `IN_PROGRESS` | При выборе типа включается корректный набор модулей/ролей/workflow | Основа есть (`agency/employer`), профиль `services` и полная автоконфигурация нужно дожать |
| 3 | Базовая работоспособность CRM | `DONE` | Можно создать клиента, кандидата, процесс/сделку, задачу, заметку, файл | Базовый сценарий закрыт |
| 4 | Коммуникации (email + мессенджеры) | `IN_PROGRESS` | Подключение, inbox, отправка, история, шаблоны, базовые настройки | Ядро готово, нужен финальный UX/ошибки и релизная стабилизация |
| 5 | Реклама и лиды | `IN_PROGRESS` | Лид приходит из источника, карточка создается, источник сохраняется | Pipeline есть, требуется полный продуктовый проход под launch |
| 6 | Командная работа | `DONE` | Инвайты, роли, права, активность доступны | Работает |
| 7 | Автоматизации | `IN_PROGRESS` | Триггеры/автодействия/распределение/автоответы доступны без костылей | Частично реализовано |
| 8 | Подписка и биллинг | `IN_PROGRESS` | План, смена, продление, отмена, история платежей | Self-service реализован, production Stripe не подключен |
| 9 | Скрытие недореализованных модулей | `IN_PROGRESS` | Пользователь не видит незавершенные/экспериментальные функции | Частично закрыто feature/module gating |
| 10 | Полноценная работа solo | `DONE` | Один пользователь проходит путь и работает без команды | Работает |
| 11 | Полноценная работа команды | `DONE` | Совместная работа с разграничением прав | Работает |
| 12 | Time To Value 5–10 минут | `IN_PROGRESS` | Новый клиент получает first value <= 10 минут | Нужен формальный замер и UX доводка |
| 13 | Простота интерфейса | `IN_PROGRESS` | Новый пользователь понимает ключевой путь без обучения | Улучшено, но нужны доработки пустых состояний и микрокопирайта |
| 14 | Надежность ошибок | `IN_PROGRESS` | Платежи/почта/интеграции/сеть обрабатываются предсказуемо | Нужны финальные recovery/fallback сценарии |
| 15 | Логичность настроек | `DONE` | Настройки разделены по ответственности, без технического шума | Реорганизация выполнена |
| 16 | Масштабируемость | `IN_PROGRESS` | Стабильная работа для 1 пользователя и командных тенантов | Нужны формальные нагрузочные проверки |
| 17 | Отсутствие тупиков | `IN_PROGRESS` | На каждом шаге есть понятный следующий action | Существенно улучшено, требуется финальный аудит |
| 18 | Минимум действий | `IN_PROGRESS` | Клиент/письмо/задача создаются за целевое число кликов | Частично выполнено, нужен UX pass |
| 19 | Empty-state UX | `IN_PROGRESS` | Пустые экраны дают следующий шаг и образец данных | Частично есть, не везде консистентно |
| 20 | Общий критерий готовности | `BLOCKED` | Полный сценарий: регистрация -> оплата -> почта -> клиент -> лид -> работа | Блокер: production Stripe + финальный E2E sign-off |

## 3.2 Текущая интегральная готовность

- Product readiness: `~80%`
- Блокер запуска self-serve продаж: `Stripe production integration`

## 3.3 Дополнительные критические критерии (21–38)

| # | Критерий | Статус | Проверка готовности | Комментарий |
|---|---|---|---|---|
| 21 | Time to First Value (реальная польза за 10–15 мин) | `IN_PROGRESS` | Пользователь проходит от регистрации до первого рабочего результата <= 15 мин | Цель: 5–10 мин |
| 22 | Empty State UX в каждом ключевом разделе | `IN_PROGRESS` | Во всех пустых экранах есть объяснение + CTA + next step | Нужно довести консистентность |
| 23 | Permission Integrity (роль/тариф/тип бизнеса/готовность модуля) | `IN_PROGRESS` | Нет утечек видимости для неподходящих ролей и тарифов | Нужен формальный role-by-role прогон |
| 24 | Failure Recovery (ошибки без потери пути) | `IN_PROGRESS` | Ошибки объясняются, прогресс не теряется, есть безопасный retry | Частично закрыто, не полностью |
| 25 | Lifecycle Retention (день 2/3/7) | `DONE` | Пользователь понимает зачем возвращаться и что делать дальше | Внедрены in-app retention nudges D1/D2/D3/D7 + day-level metrics/report в Trial Center |
| 26 | Модульность по типу бизнеса (`agency/employer/services`) | `IN_PROGRESS` | Тип бизнеса меняет модули, термины, роли, шаблоны, onboarding | `services` профиль нужно завершить |
| 27 | Progressive onboarding (обязательное сейчас / остальное потом) | `IN_PROGRESS` | Можно начать работу до полной настройки всех модулей | Сильный прогресс, нужен финальный UX pass |
| 28 | Solo-логика не хуже командной | `IN_PROGRESS` | В solo не показываются лишние командные ветки | Нужен финальный UI-аудит |
| 29 | Управление видимостью модулей | `IN_PROGRESS` | Неготовые модули скрыты полностью, платные видны как upgrade-path | Частично реализовано |
| 30 | Скорость ключевых действий (операционные KPI) | `NOT_STARTED` | Замерены и достигнуты целевые времена операций | Добавлен отдельный KPI-блок |
| 31 | Ясность терминов в интерфейсе | `IN_PROGRESS` | Термины единообразны и адаптированы под тип бизнеса | Нужно терминологическое выравнивание |
| 32 | Коммуникационный центр как ядро workflow | `IN_PROGRESS` | Переписка интегрирована в рабочие объекты (client/candidate/lead) | Нужна финальная связка всех сценариев |
| 33 | Прозрачный billing для пользователя | `IN_PROGRESS` | План/лимиты/usage/renewal/invoices/изменение тарифа на 1 экране | История платежей и live Stripe не завершены |
| 34 | Self-guided UX (система помогает, а не требует обучения) | `IN_PROGRESS` | Подсказки, понятные labels, success/error states, next steps | Частично реализовано |
| 35 | Контрольные сценарии успеха (A/B/C) | `IN_PROGRESS` | Сценарии соло/агентство/работодатель проходят end-to-end | Матрица сценариев добавлена, нужен фактический PASS прогон |
| 36 | SEO техническая готовность marketing/public surface | `DONE` | Индексация, sitemap, robots, canonical, meta/open graph, structured data и базовые Core Web Vitals в целевых пределах | Technical baseline закрыт; остается регулярный мониторинг и server-level 404 policy как non-blocking риск |
| 37 | SEO контентное наполнение для конверсии | `DONE` | Ключевые landing/feature/use-case страницы имеют целевой контент, CTA и семантические заголовки | Wave-1 контент-пакет выпущен, перелинковка и baseline tracking внедрены |
| 38 | Mobile adaptation (responsive-first) | `IN_PROGRESS` | Публичные и core CRM-экраны проходят mobile QA (320/375/390/768), без критичных overflow и с рабочими CTA | Частично закрыто, нужен формальный mobile cross-screen pass |

---

## 4. Обязательный E2E путь (Release Gate)

Сценарий считается закрытым только если пройден целиком в staging и затем в production:

1. Пользователь заходит на landing.
2. Понимает value proposition и тарифы.
3. Выбирает тариф.
4. Регистрируется.
5. Оплачивает подписку.
6. Возвращается в приложение с активной подпиской.
7. Создает workspace и выбирает тип компании.
8. Получает корректный набор модулей.
9. Подключает email.
10. Создает первого клиента.
11. Получает/создает первого лида.
12. Выполняет первое рабочее действие (задача/статус/заметка).

Release Gate = `PASS`, если:
- нет тупиковых страниц;
- нет шага, где нужен саппорт;
- ошибки оплаты/интеграций имеют понятный retry;
- путь завершается за <= 10 минут для нового пользователя.

## 4.1 KPI скорости ключевых действий (обязательные метрики)

| Действие | Цель |
|---|---|
| Регистрация | до 2–3 минут |
| Выбор тарифа + запуск аккаунта | до 2–3 минут |
| Создание первого клиента | до 30–60 секунд |
| Создание первого кандидата | до 30–60 секунд |
| Подключение почты | до 3–5 минут |
| Отправка первого письма после подключения | до 1–2 минут |
| Приглашение участника команды | до 1 минуты |
| Настройка автоответа | до 2–5 минут |
| Запуск первой автоматизации | до 5–10 минут |

Статус блока: `NOT_STARTED` (требуется инструментированный замер и отчет).

## 4.2 Контрольные сценарии успеха (обязательный release-pass)

### Сценарий A — Solo пользователь (`services`)
1. Зарегистрировался.
2. Оплатил.
3. Выбрал `services`.
4. Подключил почту.
5. Создал клиента.
6. Отправил письмо.
7. Создал задачу.
8. Настроил автоответ.
9. Начал рабочий процесс.

### Сценарий B — Агентство (`agency`)
1. Зарегистрировался.
2. Оплатил.
3. Выбрал `agency`.
4. Подключил рекламный источник.
5. Получил лид.
6. Создал клиента.
7. Создал кандидата.
8. Назначил менеджера.
9. Подключил команду и роли.
10. Запустил рабочий процесс.

### Сценарий C — Работодатель (`employer`)
1. Зарегистрировался.
2. Оплатил.
3. Выбрал `employer`.
4. Создал вакансию.
5. Создал кандидата.
6. Назначил ответственного.
7. Настроил статусы.
8. Подключил рабочую почту.
9. Начал процесс найма.

Правило приемки: релизный статус `PASS` выставляется только если сценарии `A/B/C` проходят без участия поддержки.

---

## 5. План до 100% готовности

## 5.0 P0 — Системный скелет pipeline + системные поля (высший приоритет)

| ID | Задача | Статус | DOD | Блокеры |
|---|---|---|---|---|
| P0-1 | Ввести канонические системные этапы (`new`, `in_progress`, `hired`, `declined_rejected`) | `DONE` | Каждый пользовательский этап привязан к системному | Нет |
| P0-2 | Добавить обязательную `system_stage` привязку для funnel stages | `DONE` | Нельзя создать этап без привязки | Нет |
| P0-3 | Защитить инварианты удаления этапов | `DONE` | Нельзя удалить последний этап в используемом системном bucket | Нет |
| P0-4 | Ввести системные immutable поля (`is_system`) для custom fields | `DONE` | System fields нельзя редактировать/удалять tenant UI/API | Нет |
| P0-5 | Обновить конструктор воронок (UI mapping на system stage) | `DONE` | В UI при создании/редактировании этапа обязательна привязка | Нет |
| P0-6 | Миграция существующих данных (backfill) | `DONE` | У всех текущих stages есть `system_stage`, у custom fields есть `is_system` | Нет |

Проверка целостности `P0-6` (staging DB, `2026-03-11`):
- `funnel_stages.system_stage nulls = 0`
- `funnel_stages.system_stage invalid = 0`
- `custom_field_definitions.is_system nulls = 0`

API smoke-check `P0` (staging, `2026-03-11`):
- `P0-3`: удаление последнего этапа в bucket блокируется (`409`), удаление при наличии второго этапа проходит корректно.
- `P0-4`: попытка изменить/удалить system custom field блокируется (`409`).

## 5.1 Фаза A — Коммерческий контур (критический путь)

| ID | Задача | Статус | DOD | Блокеры |
|---|---|---|---|---|
| A1 | Подключить Stripe production (`price_id`, live keys) | `NOT_STARTED` | Checkout создает реальную подписку | Доступы Stripe |
| A2 | Подключить webhook события (`checkout.session.completed`, `invoice.paid`, `customer.subscription.updated/deleted`) | `NOT_STARTED` | Статус подписки в tenant синхронизируется автоматически | A1 |
| A3 | Реализовать платежную историю в UI (`invoices/payments history`) | `NOT_STARTED` | Пользователь видит историю списаний и статусы | A2 |
| A4 | Финализировать recovery-флоу оплаты (cancel/error/retry/pending webhook) | `IN_PROGRESS` | На каждой ошибке есть понятный следующий шаг | A1/A2 |
| A5 | Прогон сквозного E2E #20 (staging -> production) | `NOT_STARTED` | Подписанный PASS протокол | A1-A4 |

### 5.1.1 Sales Unblock Execution Pack (`2026-03-12`)

Цель пакета: закрыть блокер self-serve продаж (`A1/A2`) и подготовить формальный `PASS` по `A5`.

| Шаг | Действие | Владелец | Артефакт приемки | Статус |
|---|---|---|---|---|
| S1 | Получить/проверить production доступы Stripe (live keys, webhook signing secret, product/price IDs) | `Billing/Platform` | Заполненный `.env`/secret-store + список `price_id` в runbook | `NOT_STARTED` |
| S2 | Провести dry-run checkout в production-safe режиме (минимальный тестовый tenant) | `Backend` | Лог `checkout.session.completed` + созданная подписка в Stripe и tenant | `NOT_STARTED` |
| S3 | Включить и проверить webhook цепочку (`checkout.session.completed`, `invoice.paid`, `customer.subscription.updated/deleted`) | `Backend` | Таблица соответствий `Stripe event -> tenant state` + PASS smoke | `NOT_STARTED` |
| S4 | Закрыть recovery path для ошибок оплаты (cancel/error/retry + pending webhook) | `Frontend + Backend` | Чеклист UX-веток с ожидаемым CTA и фактическим поведением | `IN_PROGRESS` |
| S5 | Выполнить release-gate прогон #20 (`staging -> production`) и зафиксировать протокол | `QA/Product` | Подписанный `PASS/FAIL` протокол по шагам раздела 4 | `NOT_STARTED` |

Правило перехода к продажам:
- Self-serve продажи можно включать только после `S1..S5 = DONE` и обновления раздела `10` со статусом сценария `A = PASS`.

## 5.2 Фаза B — Онбординг и TTV

| ID | Задача | Статус | DOD |
|---|---|---|---|
| B1 | Автопрофиль для типа `services` (модули/workflow/роли по умолчанию) | `IN_PROGRESS` | Новый tenant `services` стартует без ручных настроек |
| B2 | Доработать пресеты `agency/employer/services` (статусы, роли, подсказки) | `IN_PROGRESS` | 3 профиля создаются консистентно |
| B3 | Замерить Time To Value (5–10 мин) на 5 новых аккаунтах | `NOT_STARTED` | Отчет с медианой и узкими местами |
| B4 | Убрать обязательные advanced-настройки из первого запуска | `IN_PROGRESS` | До first value не требуется заход в Settings |
| B5 | `services` onboarding: отдельный шаг первого клиента (`first_client_created`) | `DONE` | Онбординг и activation учитывают создание первого клиента, API возвращает `clients/counterparties` счетчики |

## 5.3 Фаза C — Коммуникации и лиды (операционная ценность)

| ID | Задача | Статус | DOD |
|---|---|---|---|
| C1 | Финальный QA коммуникаций по матрице (`docs/communications-test-matrix.md`) | `IN_PROGRESS` | Все критические кейсы PASS |
| C2 | Email UX: подписи, шрифты, шаблоны, ошибки подключения | `IN_PROGRESS` | Пользователь отправляет письмо без ручной диагностики |
| C3 | Лиды: полный путь source -> lead -> assignment -> action | `IN_PROGRESS` | Источник фиксируется, распределение работает |
| C4 | Auto-assignment лидов + fallback при сбоях интеграции | `IN_PROGRESS` | Лид не теряется, есть очередь и retry |
| C5 | Конфигурируемый маппинг рекламных полей (`source -> target -> format`) | `DONE` | Админ настраивает какие поля забирать из рекламы и в какие CRM-поля сохранять |
| C6 | Явная классификация компаний (`client` / `counterparty`) для `services` аналитики | `DONE` | Тип компании задается в CRM и используется в профильной аналитике |
| C7 | Вывести `services`-KPI по `clients/counterparties` в рабочем модуле Services | `DONE` | Вкладка `Services -> Analytics` показывает профильные KPI и предупреждение о неклассифицированных компаниях |

## 5.4 Фаза D — UX качество и надежность

| ID | Задача | Статус | DOD |
|---|---|---|---|
| D1 | Empty states во всех ключевых модулях (clients/candidates/leads/messages/tasks) | `IN_PROGRESS` | В каждом empty state есть CTA + next step |
| D2 | Минимизировать действия до целевых 1–2 кликов (клиент/задача/письмо) | `IN_PROGRESS` | UX-аудит с фактическим количеством шагов |
| D3 | Финальная карта ошибок (оплата/почта/интеграции/сеть) | `IN_PROGRESS` | Каждая ошибка имеет дружелюбный текст и recovery action |
| D4 | Нагрузочная проверка базового сценария (1 пользователь -> команда) | `NOT_STARTED` | Нет критических деградаций |
| D1.1 | Единый empty-state паттерн для `clients/leads/messages/reminders` | `DONE` | В этих модулях добавлены объяснение раздела + primary CTA + secondary next step в едином UI-паттерне |
| D1.2 | Единый empty-state паттерн для `candidates/pipeline/services-orders` | `DONE` | Добавлены CTA и next-step для пустых списков кандидатов, пустого pipeline и пустого списка сервисных заказов |
| D2.1 | Сократить шаги в ключевых действиях: задача/письмо/клиент | `DONE` | `reminders`: задача создается с автодатой без обязательного ввода due_at; `messages`: получатель подставляется автоматически из диалога + `Ctrl/Cmd+Enter` отправляет сообщение; `clients`: advanced-опции в модалке скрыты по умолчанию |
| D3.1 | Friendly network/service/access errors + retry actions в core модулях | `DONE` | `leads/reminders/messages` показывают human-friendly ошибки и recovery-CTA (`Retry`, `Setup/Leads`) |
| D3.2 | Friendly error + recovery actions для `billing/email/integrations` | `DONE` | `BillingWorkspacePage`, `EmailSettingsPage`, `MetaLeadsAdminPage` используют общий `ErrorRecoveryBanner` + `getFriendlyErrorInfo` + `Retry` |
| D3.3 | Единый recovery-UI на settings коммуникаций | `DONE` | `CommunicationsMessengerSettingsPage`, `CommunicationsQueueSettingsPage`, `CommunicationsSlaSettingsPage` используют `ErrorRecoveryBanner` вместо локальных red-alert блоков |
| D3.4 | Единый recovery-UI на admin/settings core страницах | `DONE` | `UsersPage`, `RulesetVersionsPage`, `BillingTeamPage`, `CustomFieldsPage`, `CandidateProfilesPage`, `AuditLogPage`, `DeletionRequestsPage` приведены к общему error-banner стилю |
| D3.5 | Убрать legacy red-alert блоки в расширенных settings страницах | `DONE` | `TenantsPage`, `CompanyAccessPage` и оставшиеся error-секции `RulesetVersionsPage`/`BillingTeamPage` переведены на `ErrorRecoveryBanner` |
| F8.1 | Унификация secondary action controls в коммуникационных settings | `DONE` | `CommunicationsSettingsPage`, `CommunicationsMessengerSettingsPage`, `CommunicationsQueueSettingsPage`, `CommunicationsSlaSettingsPage` используют системные `btn-secondary` вместо локальных border-кнопок |
| F8.2 | Убрать “овальные” системные чипы/бэйджи | `DONE` | Базовый `.badge` в дизайн-системе переведен с `rounded-full` на `rounded-md`, `StageTag` синхронизирован с новым стилем |
| F8.3 | Унифицировать табличный паттерн на рабочих экранах | `DONE` | Таблицы в `Dashboard`, `Services (analytics)`, `VacancyDetail (candidates mini table)` переведены на единый `.table` стиль (заголовки, границы, плотность строк) |
| F8.4 | Унифицировать error/recovery в профильных модалках | `DONE` | `ApplyProfileToVacanciesModal`, `ProfileHistoryModal`, `BulkUpdateProfilesModal`, `ImportProfileModal`, `ProfileUsageStatsModal` используют `ErrorRecoveryBanner` вместо локальных rose alert-блоков |
| F8.5 | Убрать локальные rose-alert выбросы в рабочих карточках | `DONE` | `VacancyDetail (document policies)` и `Companies (document policies)` используют общий `ErrorRecoveryBanner` |
| F8.6 | Унифицировать error-state на auth-экранах | `DONE` | `Login`, `Signup`, `ForgotPassword`, `ResetPassword` используют `ErrorRecoveryBanner` вместо локальных rose-блоков |
| F8.7 | Унифицировать error/recovery в communications рабочих страницах | `DONE` | `CommunicationsSetupPage`, `CommunicationsEmailInboxPage`, `CommunicationsSlaIncidentsPage`, `CommunicationsPlannerPage`, `CommunicationsThreadPage` используют единый `ErrorRecoveryBanner` с retry/next-step |
| F8.8 | Унифицировать error-state на invite/public/availability страницах | `DONE` | `InviteAcceptPage`, `PublicPortalLanding`, `PublicScanPage`, `TimeOffRequestsPage`, `MyAvailabilityPage` переведены на `ErrorRecoveryBanner` |
| F8.9 | Убрать остаточные pill-чипы в публичных hero блоках | `DONE` | Маркерные чипы на `Login` и `PublicPortalLanding` переведены с `rounded-full` на `rounded-md` |
| F8.10 | Унифицировать error-state в крупных рабочих экранах | `DONE` | `Candidates`, `TeamAvailability`, `CommunicationsCalendar` переведены на `ErrorRecoveryBanner` для загрузочных/операционных ошибок |
| F8.11 | Закрыть остаточные локальные error-блоки в рабочих страницах | `DONE` | `Pipeline`, `DocumentsRegistry`, `CommunicationsCommandAudit`, `ClientPortal` переведены на единый `ErrorRecoveryBanner` с retry-action |
| F8.12 | Унифицировать destructive-контролы и legacy error-блоки в CRM страницах | `DONE` | `VacancyList`/`ClientLinkDetail` переведены на `ErrorRecoveryBanner`; destructive actions в `VacancyDetail`, `Companies`, `CandidateProfiles`, `CustomFields` переведены на `btn-danger` |
| F8.13 | Закрыть остаточные legacy action-controls (outline/link-style) | `DONE` | `Dashboard` (`btn-outline` -> `btn-secondary`), `ClientLinkDetail`/`AgencyClients` revoke -> `btn-danger`, `Profile` saved views delete -> `btn-danger`, `MetaLeadsAdmin` table actions -> `btn-secondary/btn-danger` |
| F8.14 | Стандартизировать оставшиеся admin/workspace red-states и action controls | `DONE` | `RulesetVersions` actions переведены на `btn-secondary/btn-danger` + diff error на `ErrorRecoveryBanner`; `Invoices` и `OnboardingCompany` error-state унифицированы; `Candidates` delete-view action переведен на `btn-danger` |
| F8.15 | Унифицировать error/recovery в внутренних формах и карточках CRM | `DONE` | `UserFormCreate`/`UserFormInvite` переведены на `ErrorRecoveryBanner`; `CandidateHeader` и `CandidateRodoSection` переведены на `ErrorRecoveryBanner`; `ServicesPage` missing-docs alert приведен к `alert-error`; `CommunicationsEmailInbox` delete-action переведен на `btn-danger` |
| F8.16 | Унифицировать конструкторы профилей и destructive actions в messenger settings | `DONE` | `ProfileDocumentConstructor`, `ProfileFieldConstructor`, `StageConstructor` переведены на `btn-danger/btn-secondary`; в `CommunicationsMessengerSettingsPage` delete/remove actions переведены на `btn-danger` |
| F8.17 | Унифицировать controls на коммуникационных рабочих экранах | `DONE` | `CommunicationsCommandAuditPage`, `CommunicationsPlannerPage`, `TimeOffRequestsPage` переведены на системные `input`/`textarea`/`btn-secondary`/`btn-primary`/`btn-danger` |
| F8.18 | Унифицировать controls в Communications Email Inbox | `DONE` | `CommunicationsEmailInboxPage` переведен с локальных `rounded border ...` классов на системные `input`/`textarea`/`btn-secondary`/`btn-primary`/`btn-danger` для header, bulk actions, folder controls, preview и compose блока |
| F8.19 | Унифицировать controls в Communications Queue/SLA settings | `DONE` | `CommunicationsQueueSettingsPage` и `CommunicationsSlaSettingsPage` переведены на системные `input`/`btn-secondary`/`btn-primary` + `alert-success` для save notices |
| F8.20 | Унифицировать controls в Communications Messenger settings | `DONE` | `CommunicationsMessengerSettingsPage` переведен на системные `input`/`btn-secondary`/`btn-danger` для account forms, templates, command templates и action controls |
| F8.21 | Унифицировать action/notice controls в Communications Quick Setup | `DONE` | `CommunicationsSetupPage` переведен на системные `btn-secondary` (next-step action) и `alert-success` (ops notice) вместо локальных ad-hoc классов |
| F8.22 | Закрыть остаточные legacy controls в Thread/Messenger pages | `DONE` | `CommunicationsThreadPage` dispatch action переведен на `btn-secondary`; `CommunicationsMessengerSettingsPage` save notice переведен на `alert-success`, checkbox labels очищены от локальных bordered-pill стилей |
| F8.23 | Унифицировать controls в Communications Messages page | `DONE` | `CommunicationsMessagesPage` переведен с локальных `rounded border ...` control/action классов на системные `input`/`textarea`/`btn-secondary`/`btn-primary`/`btn-danger` (header, thread tools, tag manager, compose, modals) |
| F8.24 | Унифицировать основные controls в Communications Calendar page | `DONE` | `CommunicationsCalendarPage` переведен на системные `input`/`textarea`/`btn-secondary`/`btn-primary`/`btn-danger` в фильтрах, batch-actions, quick-actions, create forms и навигационных CTA |
| F8.25 | Дочистить динамические controls в Communications Calendar page | `DONE` | Динамические `clsx` action-кнопки (`view toggles`, `week slot toggles`, `planner status/move/duplicate`, `resize/manage`, `reminder actions`, `quick tag toggles`) переведены на системные `btn-secondary/btn-primary/btn-danger` с сохранением active-state индикации |
| F8.26 | Дочистить динамические controls в Messages/Messenger/Thread pages | `DONE` | `CommunicationsMessagesPage` dynamic toggles переведены на `btn-secondary`; `CommunicationsMessengerSettingsPage` channel selector и status-badge унифицированы (`rounded-lg` + `badge`); `CommunicationsThreadPage` send action переведен на системный `btn-primary` |
| F8.27 | Унифицировать статусные чипы в Communications Calendar page | `DONE` | `CommunicationsCalendarPage` чипы (`day counters`, `now marker`, `event source/status/priority/tags`) переведены на единый `badge` паттерн |
| F8.28 | Унифицировать controls в Communications Thread/SLA Incidents pages | `DONE` | `CommunicationsThreadPage` top actions и dropdown items переведены на `btn-secondary`/`dropdown-item`; `CommunicationsSlaIncidentsPage` search input и group toggles переведены на `input`/`btn-secondary btn-xs` |
| F8.29 | Унифицировать action menus в Communications Messages page | `DONE` | Пункты `workflow/sla/more` dropdown-меню в `CommunicationsMessagesPage` переведены на системный `dropdown-item` с сохранением active-state окраски |
| F8.30 | Унифицировать folder controls в Communications Email Inbox | `DONE` | `CommunicationsEmailInboxPage` folder items переведены на `btn-secondary` с active-state, folder/thread tags переведены на `badge` |
| F8.31 | Унифицировать planner event pills/cards в Communications Calendar | `DONE` | `CommunicationsCalendarPage` event pills (`all-day`, `week/day timeline`) переведены на базу `badge border`; event cards переведены на `rounded-lg` базу вместо legacy `rounded border` |
| F8.32 | Ввести и применить системный `alert-info` в communications | `DONE` | Добавлен `alert-info` в `components.css`; cyan info blocks в `CommunicationsMessagesPage` и `CommunicationsMessengerSettingsPage` переведены на системный alert-паттерн |
| F8.33 | Финальный micro-polish коммуникационных карточек/календаря | `DONE` | `CommunicationsMessengerSettingsPage` channel cards получили единый `focus-ring` паттерн; `CommunicationsCalendarPage` month day-cells переведены на `rounded-lg` базу для визуальной консистентности |
| F8.34 | Унифицировать accent color в communications workflow views | `DONE` | Активные состояния и акцентные маркеры в `CommunicationsMessagesPage`, `CommunicationsEmailInboxPage`, `CommunicationsSlaIncidentsPage`, `CommunicationsMessengerSettingsPage` переведены с `cyan` на единый `brand` accent |
| F8.35 | Закрыть остаточные color/control выбросы в communications pages | `DONE` | Удалены остаточные ad-hoc `cyan/blue` стили в `CommunicationsMessengerSettingsPage`, `CommunicationsSlaIncidentsPage`, `CommunicationsCalendarPage`, `CommunicationsMessagesPage`; применены системные `alert-info` и `brand` control accents |
| F8.36 | Унифицировать базовые compose/progress/date-chip controls | `DONE` | `CommunicationsThreadPage` compose controls переведены на `input/textarea`; `CommunicationsSetupPage` progress accent переведен на `brand`; `CommunicationsMessagesPage` date divider chip переведен на `badge` |
| F8.37 | Унифицировать auxiliary chips/empty-state в communications | `DONE` | `CommunicationsSlaSettingsPage` escalation targets переведены на `badge`; пустые состояния в `CommunicationsThreadPage` и `CommunicationsMessagesPage` выровнены на `rounded-lg` dashed pattern |
| F8.38 | Финализировать brand-alignment в Communications Setup | `DONE` | `CommunicationsSetupPage` focus-ring переведен на `brand`; hero gradient переведен с `cyan/sky` на `brand`; step/progress status chips переведены на системный `badge` паттерн |
| F8.39 | Унифицировать secondary badges/cards в communications views | `DONE` | `CommunicationsSlaIncidentsPage` summary/trust/group badges переведены на `badge`; `CommunicationsMessagesPage` ops/meta badges переведены на `badge`; `CommunicationsCalendarPage` upcoming cards выровнены на `rounded-lg` |
| F8.40 | Унифицировать Candidate Card communication/quick controls | `DONE` | `CandidateCommunicationSection` переведен с локальных `cyan`-акцентов на `brand` + `alert-info`; quick-controls в `CandidateCard` переведены на системные `btn-secondary`; `StageTag` для `contacted/interview/questionnaire_submitted` выровнен под `brand` palette |
| F8.41 | Унифицировать forms/actions в Services workspace | `DONE` | `ServicesPage` (catalog/orders/detail) переведен на системные `input/textarea/btn-primary/btn-secondary`, info-select карточки на `alert-info/rounded-lg`, исправлен layout typo `items-center.justify-between` |
| F8.42 | Унифицировать controls/actions в My Availability self-service | `DONE` | `MyAvailabilityPage` переведен на системные `input/textarea/btn-primary/btn-secondary` для формы заявок, cancel-action и quick-links |
| F8.43 | Унифицировать create/diff/usage controls в Ruleset Versions | `DONE` | `RulesetVersionsPage` переведен на системные `textarea/input/btn-primary/btn-secondary/badge`; diff-списки и active-row выровнены под единый `slate/brand` паттерн |
| F8.44 | Унифицировать client-link controls/status chips в Agency Clients | `DONE` | `AgencyClientsPage` переведен на системные `input/btn-secondary/badge` для portal-link controls, edit-action, modal form inputs и status chips |
| F8.45 | Унифицировать saved-views/actions и status badges в Profile | `DONE` | `ProfilePage` переведен на системные `btn-secondary` для saved-view actions, `badge` для default/current/editable статусов и `alert-success/alert-error` для локальных сообщений |
| F8.46 | Унифицировать seat-request controls/status badges в Billing Team | `DONE` | `BillingTeamPage` переведен на системные `btn-secondary btn-xs`, `textarea`, `alert-error`, `badge` для seat-request refresh/form/status patterns |
| F8.47 | Унифицировать secondary actions в Users admin page | `DONE` | `UsersPage` переведен с `btn-ghost` на системные `btn-secondary`/`btn-secondary btn-xs` в detail-card actions, audit refresh, tenant-override и list refresh controls |
| F8.48 | Унифицировать secondary actions в Tenants admin access flows | `DONE` | `TenantsPage` очищен от `btn-ghost` в seat requests/access/module-overrides сценариях; применен единый `btn-secondary`/`btn-secondary btn-xs` паттерн |
| F8.49 | Унифицировать controls/actions в Meta Leads admin page | `DONE` | `MetaLeadsAdminPage` переведен с ad-hoc кнопок/инпутов на системные `btn-primary/btn-secondary/input/textarea`, success notice выровнен на `alert-success`, actions в logs/modal приведены к системному паттерну |
| F8.50 | Унифицировать mapping form/search controls в Meta Leads | `DONE` | `MetaLeadsAdminPage` mapping-flow переведен на системные `input`/`btn-primary` (ad_id, vacancy_id, note, save, search), убраны остаточные `rounded border ...` controls |
| F8.51 | Унифицировать tab/pagination secondary controls в Audit Log | `DONE` | `AuditLogPage` переведен с ad-hoc tab-кнопок и `btn-ghost` на системные `btn-primary/btn-secondary btn-sm` для tabs, refresh и pagination actions |
| F8.52 | Унифицировать form secondary actions в Legal Documents | `DONE` | `LegalDocumentsPage` очищен от `btn-ghost` в create-version flow: cancel/add-version actions переведены на системные `btn-secondary`/`btn-secondary btn-sm` |
| F8.53 | Унифицировать secondary actions в admin profile/access/forms пакете | `DONE` | `CandidateProfilesPage`, `CompanyAccessPage`, `DeletionRequestsPage`, `CustomFieldsPage`, `TenantLinksSettingsPage` очищены от `btn-ghost`/link-style secondary actions и переведены на системные `btn-secondary` (`btn-sm/btn-xs` где уместно) |
| F8.54 | Унифицировать secondary actions в processing/documents/agency flows | `DONE` | `DoProcesowaniaPage`, `DocumentsRegistryPage`, `AgencyClientsPage` очищены от `btn-ghost` и приведены к системным `btn-secondary` (`btn-sm/btn-xs`, pagination/filter/reset/advanced actions) |
| F8.55 | Унифицировать secondary actions в vacancy/candidate/invoices модалках | `DONE` | `VacancyForm`, `VacancyDetail`, `CandidateCard`, `ClientInvoicesBlock` очищены от `btn-ghost`; secondary controls приведены к системным `btn-secondary` (`btn-sm` где уместно) |
| F8.56 | Унифицировать secondary actions в candidate bulk modals | `DONE` | `BulkManagerModal`, `BulkHandoffModal`, `BulkTagsModal`, `BulkVacancyModal`, `BulkDeleteModal`, `BulkStageModal` очищены от `btn-ghost`; cancel/secondary actions приведены к `btn-secondary` |
| F8.57 | Унифицировать secondary/destructive controls в candidate sections | `DONE` | `CandidateNotesSection`, `CandidateRemindersSection`, `CandidateContactAttemptsSection`, `CandidateBasicSection`, `CandidateExperienceSection`, `CandidateHandoffSection` очищены от `btn-ghost`; secondary-actions переведены на `btn-secondary`, row-delete в experience — на `btn-danger` |
| F8.58 | Унифицировать secondary controls в Candidates page | `DONE` | `CandidatesPage` очищен от остаточных `btn-ghost` в filter reset, bulk clear, context/actions menu, save-view и saved-views apply action; применен системный `btn-secondary` (`btn-xs` где уместно) |
| F8.59 | Унифицировать secondary controls в Reminders page | `DONE` | `RemindersPage` очищен от `btn-ghost` в quick composer, filters, task/event actions и edit modal cancel; применен системный `btn-secondary` (`btn-sm/btn-xs` где уместно) |
| F8.60 | Унифицировать secondary/destructive controls в shared workspace views | `DONE` | `PipelinePage`, `DashboardPage`, `Topbar`, `UserTable`, `ColumnFilterMenu`, `DocumentWorkflow`, `DocumentCard` очищены от `btn-ghost`; secondary actions переведены на `btn-secondary`, document reject/delete actions — на `btn-danger` |
| F8.61 | Унифицировать secondary/destructive controls в Companies workflows | `DONE` | `CompaniesPage` очищен от остаточных `btn-ghost` в detail/list/policy flows; add/edit/reset/cancel actions переведены на `btn-secondary`, remove/delete/archive actions — на `btn-danger` (restore — `btn-secondary`) |
| F8.62 | Удалить legacy `btn-ghost` из дизайн-системы | `DONE` | После полной миграции UI-контролов удален CSS-класс `.btn-ghost` из `components.css`; в `src` не осталось его использований |

## 5.5 Фаза E — Multi-tenant и Auth детализация (из source docs)

| ID | Задача | Статус | DOD |
|---|---|---|---|
| E1 | Citronex flow: tenant-linked client visibility (vacancies/candidates scope) | `NOT_STARTED` | Tenant с лицензией видит корректный скоуп без ручных правок |
| E2 | POLTRAK flow: portal-link access for client without tenant | `NOT_STARTED` | Клиент без лицензии проходит сценарий только по защищенной ссылке |
| E3 | Tenant links policy hardening (handoff/visibility/audit) | `NOT_STARTED` | Настройки и видимость формально проверены в E2E |
| E4 | Auth hardening for self-serve launch (signup/invite/session recovery) | `DONE` | Нет тупиков в auth-сценариях, recovery покрыт |
| E5 | Communications depth checklist (scheduler/OAuth/webhooks/audit consistency) | `IN_PROGRESS` | Все обязательные domain-checks имеют PASS статус |

## 5.6 Фаза F — UX целостность и retention (новые критические критерии)

| ID | Задача | Статус | DOD |
|---|---|---|---|
| F1 | Измерить и сократить Time To First Value до <= 10–15 минут | `IN_PROGRESS` | Подтвержденный TTFV по новым аккаунтам |
| F2 | Довести empty states во всех ключевых модулях до единого стандарта | `IN_PROGRESS` | В каждом разделе есть explanation + CTA + next step |
| F3 | Permission integrity аудит по ролям (`superadmin/owner/admin/manager/user`) | `IN_PROGRESS` | Нет конфликтов видимости, подтверждено тест-матрицей |
| F4 | Failure recovery matrix (оплата, интеграции, сеть, прерывание onboarding) | `IN_PROGRESS` | При ошибке путь пользователя сохраняется и продолжается |
| F5 | Lifecycle retention path (день 1/2/3/7) | `DONE` | Для каждого дня есть понятный next-step и ценность |
| F6 | Терминологическая унификация UI по типам бизнеса | `DONE` | Нет конфликтующих терминов в интерфейсе |
| F7 | Сценарии успеха A/B/C — формальный прогон и фиксация PASS/FAIL | `IN_PROGRESS` | Все три сценария закрыты без саппорта |
| F8 | Compact CRM UI standard + Tabler icons rollout | `IN_PROGRESS` | Ключевые экраны (`Pipeline`, `Leads`, `Candidates`, `Dashboard`) визуально компактны, единообразны и без лишних элементов |
| F9 | SEO optimization baseline (technical SEO) | `DONE` | Публичные страницы имеют корректные `title/description/canonical`, `robots.txt`, `sitemap.xml`, OG tags, schema.org и индексацию без критичных ошибок |
| F10 | SEO content rollout (pages + copy + intent mapping) | `DONE` | Выпущен контент-пакет для приоритетных запросов (landing/use-cases/features), есть внутренняя перелинковка и конверсионные CTA |
| F11 | Mobile adaptation pass (public + CRM core) | `IN_PROGRESS` | Пройден responsive-аудит по брейкпоинтам `320/375/390/768`, устранены критичные UI/UX разрывы, оформлен mobile QA-report |

Стандарт `F8` (принят):
- Навигация и аккаунт-меню строятся по responsibility-first: `My account` и `Company overview`.
- В аккаунт-меню выводятся только релевантные действия по permission (без технических пунктов и дублей).
- Приоритет компактной плотности: короткие заголовки, ясные CTA, минимум декоративных блоков.

### 5.6.1 Декомпозиция `F9` (technical SEO baseline)

| ID | Задача | Статус | DOD |
|---|---|---|---|
| F9.1 | Зафиксировать SEO-инвентарь публичных URL (`landing/features/use-cases/pricing/auth-public`) | `DONE` | Есть полный список indexable страниц и владельцев |
| F9.2 | Выровнять `title/description/canonical/og:*` по всем indexable страницам | `DONE` | На каждой странице корректные мета-теги без дублей canonical |
| F9.3 | Проверить и обновить `robots.txt` + `sitemap.xml` (включая auto-generation) | `DONE` | Поисковые боты получают актуальные правила и полный sitemap без битых URL |
| F9.4 | Добавить schema.org (`Organization`, `SoftwareApplication`, `FAQ/Article` где уместно) | `DONE` | Structured data проходит валидацию без критичных ошибок |
| F9.5 | Техпроверка индексации и crawlability (`noindex`, redirects, 404/soft-404) | `DONE` | Нет критичных indexability проблем на приоритетных страницах |
| F9.6 | Базовый CWV-pass публичных страниц (LCP/CLS/INP) | `DONE` | По приоритетным URL нет блокирующих деградаций производительности |

### 5.6.1.1 `F9.1` SEO URL Inventory (baseline, `2026-03-12`)

| URL | Тип | Index target | Владелец |
|---|---|---|---|
| `/` | CRM marketing landing | `YES` | Frontend + Product marketing |
| `/pricing` | CRM pricing landing alias | `YES` | Frontend + Product marketing |
| `/signup` | Self-serve conversion entry | `YES` | Frontend + Growth |
| `/login` | Auth entry | `YES` | Frontend |
| `/public/intake` | Candidate portal landing | `YES` | Frontend + Operations |
| `/public/portal` | Candidate portal promo | `YES` | Frontend + Operations |
| `/legal/terms.html` | Legal static | `YES` | Product + Legal |
| `/legal/privacy.html` | Legal static | `YES` | Product + Legal |
| `/legal/cookies.html` | Legal static | `YES` | Product + Legal |
| `/data-deletion.html` | Legal static | `YES` | Product + Legal |
| `/app/*` | Authenticated workspace | `NO` | Frontend |
| `/public/apply/:token` | Tokenized candidate flow | `NO` | Frontend |
| `/public/apply-old/:token` | Legacy tokenized candidate flow | `NO` | Frontend |
| `/public/status/:token` | Tokenized status flow | `NO` | Frontend |
| `/public/scan*` | Session-bound scanning flow | `NO` | Frontend |

### 5.6.1.2 `F9.5` Crawlability Audit Snapshot (`2026-03-12`)

| URL / pattern | Ожидаемое поведение | Реализация | Статус |
|---|---|---|---|
| `/`, `/pricing`, `/signup`, `/login`, `/public/intake`, `/public/portal` | `index,follow` + canonical/OG | `useSeoMeta` на indexable страницах | `PASS` |
| `/app/*` | `noindex,nofollow` | `useRobotsMeta` в `AppShell` | `PASS` |
| `/public/apply/:token`, `/public/apply-old/:token`, `/public/status/:token`, `/public/scan*` | `noindex,nofollow` | `useRobotsMeta` в tokenized public страницах | `PASS` |
| `/client-portal?token=...` | `noindex,nofollow` | `useRobotsMeta` в `ClientPortalPage` | `PASS` |
| `/forgot-password`, `/reset-password`, `/invite/accept` | `noindex,nofollow` | `useRobotsMeta` в auth utility страницах | `PASS` |
| неизвестные public URL (`*`, when unauth) | Не должны мягко индексироваться как home | отдельная `PublicNotFoundPage` + `noindex,nofollow` вместо редиректа на `/` | `PASS` |

Residual risk:
- Для SPA в статическом хостинге сервер может возвращать `200` для неизвестных URL (soft-404 на уровне HTTP). На уровне UI/SEO мета это смягчено `PublicNotFoundPage` + `noindex,nofollow`; для полного закрытия нужен server-level `404` response policy.

### 5.6.1.3 `F9.6` CWV Static Pass Snapshot (`2026-03-12`)

| Шаг | Изменение | Наблюдение |
|---|---|---|
| Font loading hints | добавлены `dns-prefetch` для `fonts.googleapis.com`/`fonts.gstatic.com` | снижены риски DNS/TLS latency перед загрузкой шрифтов |
| Hero media hint | `/public/portal` hero image переведен на `loading="eager"` + `fetchPriority="high"` | улучшен приоритет вероятного LCP media |
| Public route code-splitting | `public apply/scan/status/intake-new` и `client-portal` переведены на lazy chunks | в build появились отдельные чанки (`~4–109KB`), основной `index` bundle снижен до `~5.23MB` |
| Render deferral below-the-fold | в `CRM landing` и `Public portal` секциях ниже hero включен `content-visibility:auto` (`.cv-auto`) | уменьшена начальная render cost для длинных маркетинговых страниц |

Residual risk:
- Требуется регулярный lab/field мониторинг (`Lighthouse`/RUM) после релизов, чтобы ловить регрессии CWV при росте контента и JS-чанков.

### 5.6.2 Декомпозиция `F10` (SEO content rollout)

| ID | Задача | Статус | DOD |
|---|---|---|---|
| F10.1 | Собрать keyword-intent карту (`landing`, `feature`, `use-case`, `comparison`) | `DONE` | Есть приоритизированный backlog страниц с целевым intent |
| F10.2 | Подготовить шаблон контент-страниц (H1/H2, CTA, internal links, FAQ) | `DONE` | Есть единый template для массовой публикации |
| F10.3 | Выпустить пакет приоритетных страниц wave-1 | `DONE` | Опубликованы основные страницы с согласованной семантикой и CTA |
| F10.4 | Встроить внутреннюю перелинковку между landing/features/use-cases | `DONE` | Все страницы wave-1 связаны по intent-цепочкам |
| F10.5 | Проверить конверсионные CTA и аналитические события контента | `DONE` | На каждой SEO-странице есть измеряемый conversion path |

### 5.6.2.1 `F10.1` Keyword-Intent Map (baseline, `2026-03-12`)

| Cluster | Keyword intent | Поисковый интент | Target URL | Priority wave | Владелец |
|---|---|---|---|---|---|
| Landing (core) | recruitment crm | Commercial investigation | `/` | `Wave-1` | Product marketing + Frontend |
| Landing (geo) | crm for recruitment agency | Commercial investigation | `/` | `Wave-1` | Product marketing + Frontend |
| Landing (geo) | crm dla agencji rekrutacyjnej | Commercial investigation | `/` | `Wave-1` | Product marketing + Frontend |
| Pricing | recruitment crm pricing | Transactional/comparison | `/pricing` | `Wave-1` | Product marketing |
| Pricing | crm pricing for recruiters | Transactional/comparison | `/pricing` | `Wave-1` | Product marketing |
| Feature | candidate pipeline software | Commercial investigation | `/features/candidate-pipeline` (planned) | `Wave-1` | Product marketing + Frontend |
| Feature | recruitment document management | Commercial investigation | `/features/document-control` (planned) | `Wave-1` | Product marketing + Frontend |
| Feature | recruitment team collaboration crm | Commercial investigation | `/features/team-workflow` (planned) | `Wave-2` | Product marketing |
| Use-case | crm for trucking recruitment | Commercial investigation | `/use-cases/trucking-recruitment` (planned) | `Wave-1` | Product marketing + Ops |
| Use-case | high volume candidate onboarding | Problem/solution | `/use-cases/high-volume-onboarding` (planned) | `Wave-1` | Product marketing + Ops |
| Comparison | hostflow vs spreadsheets recruitment | Alternative comparison | `/comparison/hostflow-vs-spreadsheets` (planned) | `Wave-2` | Product marketing |
| Comparison | recruitment crm vs ats | Alternative comparison | `/comparison/recruitment-crm-vs-ats` (planned) | `Wave-2` | Product marketing |

### 5.6.2.2 `F10.2` Content Template Pack (`2026-03-12`)

- Source template: [content-page-template.md](/opt/HostFlow/docs/seo/content-page-template.md)
- Template covers required structure for wave pages:
  - metadata (`title/description/canonical/og`)
  - hero (`H1 + value + dual CTA`)
  - core sections (`problem/solution/workflow/proof/objections`)
  - internal linking minimums
  - FAQ + JSON-LD guidance
  - baseline conversion tracking events

### 5.6.2.3 `F10.3/F10.4` Wave-1 Publication Snapshot (`2026-03-12`)

| URL | Тип | Статус | CTA | Internal links |
|---|---|---|---|---|
| `/features/candidate-pipeline` | Feature | `PUBLISHED` | `signup + pricing` | links to other wave-1 pages |
| `/features/document-control` | Feature | `PUBLISHED` | `signup + pricing` | links to other wave-1 pages |
| `/use-cases/trucking-recruitment` | Use-case | `PUBLISHED` | `signup + pricing` | links to other wave-1 pages |
| `/use-cases/high-volume-onboarding` | Use-case | `PUBLISHED` | `signup + pricing` | links to other wave-1 pages |
| `/comparison/hostflow-vs-spreadsheets` | Comparison | `PUBLISHED` | `signup + pricing` | links to comparison + feature pages |
| `/comparison/recruitment-crm-vs-ats` | Comparison | `PUBLISHED` | `signup + pricing` | links to comparison + feature/use-case pages |
| `/` (`CrmLandingPage`) | Landing hub | `UPDATED` | existing landing CTA | added guide links to all wave-1 pages |

Supporting implementation:
- Routes wired in `hostflow-frontend/src/App.tsx`.
- URLs included in auto-generated sitemap (`scripts/generate-sitemap.mjs` -> `public/sitemap.xml`).

### 5.6.2.4 `F10.5` Conversion Tracking Snapshot (`2026-03-12`)

| Event | Trigger | Coverage |
|---|---|---|
| `seo_cta_click` | клики по primary/secondary/related CTA | `CrmLandingPage` + все wave-1 feature/use-case страницы |
| `seo_scroll_depth` | milestone глубины скролла `25/50/75/100` | `CrmLandingPage` + все wave-1 feature/use-case страницы |

Implementation notes:
- Tracking hook: `hostflow-frontend/src/hooks/useSeoTracking.ts`.
- Transport: `window.dataLayer` (vendor-agnostic baseline).

### 5.6.3 Декомпозиция `F11` (mobile adaptation pass)

| ID | Задача | Статус | DOD |
|---|---|---|---|
| F11.1 | Составить mobile QA-матрицу экранов (`public + CRM core`) | `DONE` | Зафиксирован список экранов и breakpoints `320/375/390/768` |
| F11.2 | Провести cross-screen аудит на overflow/clip/tap-target issues | `DONE` | Критичные баги `MOB-001..004` заведены и закрыты; residual risks зафиксированы |
| F11.3 | Закрыть P0/P1 mobile-баги по ключевому пути (`signup -> onboarding -> first value`) | `DONE` | Текущий P0/P1 backlog по mobile закрыт, блокирующих дефектов не осталось |
| F11.4 | Проверить таблицы/формы/модалки на touch-friendly взаимодействие | `IN_PROGRESS` | Основные CRUD-сценарии устойчивы в mobile viewport; базовый modal touch-baseline внедрен |
| F11.5 | Зафиксировать финальный mobile QA-report с PASS/FAIL по каждому экрану | `IN_PROGRESS` | Release-report v1 зафиксирован (static pass), manual device QA pending |

### 5.6.4 `F11.1` Mobile QA Matrix (baseline, `2026-03-12`)

| Область | Route / экран | Приоритет | 320 | 375 | 390 | 768 | Статус |
|---|---|---|---|---|---|---|---|
| Public | `/` (`CrmLandingPage`) | `P0` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| Auth | `/signup` (`SignupPage`) | `P0` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| Auth | `/login` (`Login`) | `P0` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| Onboarding | `/app/onboarding/company` | `P0` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| Onboarding | `/app/onboarding/getting-started` | `P0` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| CRM Core | `/app/overview` (`Dashboard`) | `P1` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| CRM Core | `/app/clients` (`AgencyClientsPage`) | `P1` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| CRM Core | `/app/leads` (`LeadsPage`) | `P1` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| CRM Core | `/app/messages` (`CommunicationsMessagesPage`) | `P1` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| CRM Core | `/app/reminders` (`RemindersPage`) | `P1` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| Public Intake | `/public/scan` (`PublicScanPage`) | `P1` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |
| Settings | `/app/settings` (`SettingsLandingPage`) | `P2` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `PASS_STATIC` | `IN_PROGRESS` |

Покрытие матрицы:
- Breakpoints: `320/375/390/768`.
- Источник маршрутов: `hostflow-frontend/src/App.tsx`, `hostflow-frontend/src/app/routes.tsx`.
- Формат фиксации результата для каждой ячейки: `PASS` / `FAIL(<BUG_ID>)`.
- Текущее обозначение: `PASS_STATIC` = code/UI static audit pass, требуется manual device verification для финального `PASS`.

### 5.6.5 `F11.2` Mobile Bug Backlog (cross-screen audit)

| Bug ID | Severity | Область | Симптом | Доказательство | Статус | Владелец |
|---|---|---|---|---|---|---|
| `MOB-001` | `P1` | App topbar (authenticated) | Риск горизонтального выхода dropdown за viewport на `320px` из-за фиксированной ширины | `hostflow-frontend/src/components/nav/Topbar.tsx` (`w-[320px] -> w-[min(96vw,320px)]`) | `DONE` | Frontend |
| `MOB-002` | `P2` | Pipeline side panel | Для узких экранов есть риск перекрытия рабочего контента фиксированной панелью `w-96` | `hostflow-frontend/src/pages/Pipeline.tsx` (`w-96 -> w-full sm:w-96`, main offset `mr-96 -> mr-0 sm:mr-96`) | `DONE` | Frontend |
| `MOB-003` | `P2` | CRM landing pricing block | Контент pricing таблицы уходит в горизонтальный скролл; нужен UX-check на удобство swipe/CTA | `hostflow-frontend/src/pages/public/CrmLandingPage.tsx` (mobile cards `md:hidden` + desktop table `hidden md:block`) | `DONE` | Frontend + Product |
| `MOB-004` | `P1` | Modal forms/actions | В модалках не было гарантированного touch target `44px` и ограничителя высоты на маленьких экранах | `hostflow-frontend/src/components/Modal.tsx`, `hostflow-frontend/src/styles/components.css` (`modal-surface`, `min-h-[44px]`, mobile `max-h`) | `DONE` | Frontend |

Правило triage:
- `P0/P1` баги блокируют закрытие `F11.3`.
- `P2` баги допускаются в релиз только с явным mitigation и записью residual risk в `F11.5`.

### 5.6.6 `F11.4` Touch-friendly Audit Snapshot (`2026-03-12`)

| Область | Проверка | Статус | Доказательство |
|---|---|---|---|
| Modal shell | Модалка не выходит за viewport и доступна для скролла на mobile | `PASS` | `hostflow-frontend/src/components/Modal.tsx` (`max-h` + `overflow-y-auto`) |
| Modal controls | CTA/inputs в модалках соответствуют touch baseline | `PASS` | `hostflow-frontend/src/styles/components.css` (`.modal-surface` + `min-h-[44px]`) |
| Candidate bulk modals | Stage/Manager/Vacancy bulk flows используют единый modal touch baseline | `PASS` | `hostflow-frontend/src/modules/candidates/components/BulkStageModal.tsx`, `BulkManagerModal.tsx`, `BulkVacancyModal.tsx` |
| Остаточный аудит CRUD table/forms | Требуется ручной cross-screen прогон `320/375/390/768` по рабочим таблицам и inline form controls | `IN_PROGRESS` | Остается как часть `F11.4` до финального `F11.5` report |

### 5.6.7 `F11.4` CRUD Table/Forms Matrix (touch baseline, static pass `2026-03-12`)

| Экран | 320 | 375 | 390 | 768 | Статус | Доказательство |
|---|---|---|---|---|---|---|
| `/app/candidates` | `PASS` | `PASS` | `PASS` | `PASS` | `IN_PROGRESS` | `hostflow-frontend/src/pages/Candidates.tsx` (controls через `.input`/`.btn-*`), `hostflow-frontend/src/styles/components.css` (global `min-h`) |
| `/app/clients` | `PASS` | `PASS` | `PASS` | `PASS` | `IN_PROGRESS` | `hostflow-frontend/src/pages/Companies.tsx` (forms/actions на `.input`/`.btn-*`), `hostflow-frontend/src/styles/components.css` |
| `/app/leads` | `PASS` | `PASS` | `PASS` | `PASS` | `IN_PROGRESS` | `hostflow-frontend/src/pages/LeadsPage.tsx` (`input/btn` с локальным `h-9`, но touch baseline обеспечен global `min-h`) |
| `/app/settings` | `PASS` | `PASS` | `PASS` | `PASS` | `IN_PROGRESS` | `hostflow-frontend/src/pages/admin/SettingsLandingPage.tsx` + системные controls из `components.css` |

Ограничение текущего статуса:
- Матрица фиксирует `touch-target baseline` (размер controls), но финальный `F11.5` требует ручной визуальный QA для overflow/keyboard-safe поведения на реальных девайсах.

### 5.6.8 `F11.5` Mobile QA Report v1 (`2026-03-12`)

Итог v1:
- `P0/P1 mobile backlog`: `CLOSED` (см. `MOB-001..004`).
- `Static QA по приоритетным route`: `PASS_STATIC`.
- `Blocking defects`: `0` (по статическому аудиту).
- `Release decision (mobile)`: `GO_WITH_MANUAL_QA_PENDING`.

Residual risks до финального `PASS`:
- Отсутствует device-level проверка soft keyboard overlap (`iOS Safari` / `Android Chrome`) для длинных форм и modal scroll.
- Не выполнен ручной swipe/tap comfort-pass на реальных устройствах (проверка удобства, а не только размеров controls).
- Не зафиксирован screenshot-based отчет по каждой странице/брейкпоинту.

Критерий закрытия `F11.5`:
- Провести manual run по матрице `320/375/390/768` с фиксацией `PASS/FAIL`, скриншотами и списком residual risks.
- После этого перевести ячейки `PASS_STATIC` в финальный `PASS`.

### 5.6.9 `F5` Lifecycle Retention Snapshot (`2026-03-12`)

Что внедрено:
- В `Dashboard` добавлен in-app retention nudge для trial-tenant по возрасту workspace (`tenant.created_at`): day buckets `D1/D2/D3/D7`.
- Для каждого bucket показывается конкретный `next-step` CTA на основе фактического onboarding status (`/onboarding/status`):
  - если не создана компания -> `/app/onboarding/company`;
  - если не выполнен type-specific шаг -> `/app/leads` / `/app/vacancies` / `/app/clients`;
  - если не создан `next action` -> `/app/reminders`;
  - если activation закрыт -> `/app/settings/billing`.
- Добавлен мягкий dismiss (`Hide for now`) с tenant/day-scoped persistence в `localStorage` (`hf:trial-retention:<tenant_id>:d<day>`), чтобы nudge не повторялся навязчиво в пределах одного bucket.
- Добавлен baseline retention tracking через `window.dataLayer`:
  - `trial_retention_nudge` (`action=impression`);
  - `trial_retention_nudge` (`action=cta_click`);
  - `trial_retention_nudge` (`action=dismiss`).
- Добавлен backend ingest и агрегированный отчет retention:
  - `POST /api/v1/analytics/events` (сохраняет `trial_retention_nudge` в `activity_log`);
  - `GET /api/v1/analytics/trial-retention?days=30` (day-level buckets `d1/d2/d3/d7`, impressions/clicks/dismiss/CTR).
- В `Dashboard` (`Trial Center`) добавлена таблица retention-метрик за `30d` для admin/supervisor.

Текущий статус:
- `F5`: `DONE` (in-app путь D1/D2/D3/D7 + day-level metrics/report внедрены).

### 5.6.10 `F6` Terminology Unification Snapshot (`2026-03-12`)

Что внедрено (wave-1):
- Добавлен канонический словарь терминов: [business-terminology-map.md](/opt/HostFlow/docs/ux/business-terminology-map.md).
- В `Dashboard` убран конфликтный label `Clients / Companies`; для `agency` используется единый термин `Clients`.
- В `Dashboard` введены business-aware термины для entity-блока:
  - `employer`: `Company/Companies`;
  - `agency/services`: `Client/Clients`.
- Термины применены в ключевых KPI и таблице entity-overview (`global stats`, `companies widget` title/header/empty).
- В `AgencyClientsPage` secondary CTA в empty-state выровнен на `Open clients` (вместо `Open companies`), чтобы не расходиться с названием раздела.
- Добавлены i18n-термины `app.dashboard.terms.*` для `en/ru/pl` (`clients/company` singular/plural).

Что внедрено (wave-2):
- `Sidebar`: label раздела `/app/clients` теперь business-aware (`Clients` для `agency/services`, `Companies` для `employer`).
- `Topbar` quick-search targets: label для `/app/clients` синхронизирован с business-aware термином.
- `Breadcrumbs`: title и crumb для `/app/clients` синхронизированы с business-aware термином.
- `LeadsPage` и `ServicesPage` empty-state CTA на `/app/clients` переведены на business-aware label (через единый helper).
- `OnboardingGettingStartedPage` и `OnboardingWizard`: CTA на `/app/clients` переведены на business-aware label (`Open clients` / `Open companies`); в `OnboardingGettingStartedPage` сервисный шаг использует динамический entity-термин (`Create first client/company`).
- `AgencyClientsPage` и `ClientLinkDetailPage`: secondary copy-pass завершен (back/not-found/empty/add/success copy используют business-aware entity terms в user-facing CTA и headers).
- Добавлен общий hook `useBusinessTerminology` для канонического использования терминов в UI-слое.

Текущий статус:
- `F6`: `DONE` (dashboard + nav/topbar/breadcrumb + onboarding + secondary screens выровнены по business-aware `client/company` терминологии).

---

## 6. Единая структура настроек (принято)

Целевая IA настроек (принята и внедрена):

- `Workspace`
- `CRM Setup`
- `Team`
- `Automations`
- `Integrations`
- `Billing`
- `Personal`

Правило: системные платформенные настройки (`Super Admin`) не показываются tenant-пользователям.

---

## 7. Контроль доступа и видимости модулей

Обязательные правила релиза:
- Нереализованные модули полностью скрыты из навигации и маршрутов.
- Экспериментальные функции доступны только под feature flag.
- Пользователь видит только то, на что у него есть роль и entitlement.

Статус: `IN_PROGRESS` (основа реализована, нужен финальный аудит маршрутов и пустых пунктов меню).

---

## 8. Регламент обновления SSOT

При любом апдейте:
1. Обновить статус задачи в разделе 5.
2. Добавить подтверждение (файл/маршрут/API/тест) в `Комментарий` или в changelog.
3. Если добавляется новая задача, включить ее в соответствующую фазу и задать DOD.

---

## 9. F3 Audit Snapshot (Permission Integrity)

Дата: `2026-03-11`

### 9.1 Роли для обязательного прогона
- `superadmin`
- `owner/administrator`
- `admin/supervisor`
- `recruiter/manager`
- `regular user` (`viewer`, `client_processor`)

### 9.2 Проверки и фактические результаты

| Проверка | Статус | Доказательство / комментарий |
|---|---|---|
| Route guard применяется для всех `APP_ROUTES` | `PASS` | `App.tsx` + `RoutePermissionGuard.tsx` |
| Sidebar и маршруты используют единую permission-модель | `PASS` | После фикса маршрута `/app/settings` на `settings.view` |
| `Settings` доступен ролям с `settings.view` без ложного deny | `PASS` | Исправлено в `hostflow-frontend/src/app/routes.tsx` |
| `Users` экран согласован с `users.view/users.manage/admin.users` | `PASS` | Исправлено в `hostflow-frontend/src/app/routes.tsx` |
| Module/entitlement gating для communications включен | `PASS` | `withCommFeature`, `withCommAnyFeature`, backend access rules |
| Неготовые модули полностью скрыты во всех ролях | `IN_PROGRESS` | Нужен финальный route-by-route аудит |

### 9.3 Выявленные и закрытые разрывы
- Закрыт разрыв: `NAV settings.view` vs route `/app/settings` с `admin.users`.
- Закрыт разрыв: `UsersPage` поддерживает `users.view`, но route раньше не допускал `users.view`.

Оставшиеся действия:
- Провести формальный role-by-role прогон по всем nav/route/module combinations.
- Зафиксировать таблицу PASS/FAIL по ролям в этом разделе.

## 10. F7 Scenario Execution Board (A/B/C)

Дата: `2026-03-12`  
Протокол: [f7-scenario-protocol.md](/opt/HostFlow/docs/manual-checklist/f7-scenario-protocol.md)

| Сценарий | Статус | Блокер | Комментарий |
|---|---|---|---|
| A — Solo (`services`) | `BLOCKED` | `A1/A2` (production Stripe + webhooks) | До оплаты путь неполный, финальный `PASS` невозможен |
| B — Agency (`agency`) | `IN_PROGRESS` | Manual run + sign-off | Code/UI static прогон = `PASS_STATIC`; нужен формальный ручной E2E протокол по шагам `4.2` |
| C — Employer (`employer`) | `IN_PROGRESS` | Manual run + sign-off | Code/UI static прогон = `PASS_STATIC`; нужен формальный ручной E2E протокол по шагам `4.2` |

Правило фиксации:
- Каждый сценарий получает `PASS` только после полного прогона по шагам из раздела `4.2`.
- Для каждого прогона обязательно сохранять дату, тестовый tenant и результат (`PASS/FAIL`) в этот раздел.

### 10.1 Журнал прогонов (операционный)

| Дата | Сценарий | Окружение | Tenant | Результат | Evidence | Owner |
|---|---|---|---|---|---|---|
| `2026-03-12` | A (`services`) | staging | `N/A` | `BLOCKED` | Внешний блокер: production Stripe + webhooks (`A1/A2`) не подключены | Product/Eng |
| `2026-03-12` | B (`agency`) | staging | `N/A` (static board update) | `IN_PROGRESS` | UI/code pass зафиксирован в SSOT (`PASS_STATIC`), ожидается ручной E2E run по `4.2` с evidence | Product/QA |
| `2026-03-12` | C (`employer`) | staging | `N/A` (static board update) | `IN_PROGRESS` | UI/code pass зафиксирован в SSOT (`PASS_STATIC`), ожидается ручной E2E run по `4.2` с evidence | Product/QA |

### 10.2 Next Actions Для `F7`

1. Провести ручной E2E прогон сценария `B` по run-sheet: [f7-scenario-b-agency.md](/opt/HostFlow/docs/manual-checklist/f7-scenario-b-agency.md), затем записать `PASS/FAIL` + evidence в `10.1`.
2. Провести ручной E2E прогон сценария `C` по run-sheet: [f7-scenario-c-employer.md](/opt/HostFlow/docs/manual-checklist/f7-scenario-c-employer.md), затем записать `PASS/FAIL` + evidence в `10.1`.
3. После подключения production Stripe/webhooks снять блокер `A` и выполнить полный прогон сценария `A`.

## 11. Changelog

- `2026-03-11` — создан единый SSOT-файл готовности CRM к запуску продаж, консолидированы критерии, статусы и дорожная карта до 100%.
- `2026-03-11` — добавлена матрица покрытия источников и фаза E для закрытия требований, которые были агрегированы слишком высокоуровнево.
- `2026-03-11` — добавлены критические критерии `21–35`, KPI скорости действий, контрольные сценарии успеха `A/B/C` и фаза F (UX/permissions/recovery/retention).
- `2026-03-11` — запущены в работу `F3/F7`: добавлен audit snapshot по permission integrity и execution board сценариев `A/B/C`; исправлены route-permission разрывы для `Settings` и `Users`.
- `2026-03-11` — добавлен приоритет `P0`: системный скелет этапов pipeline + системные immutable поля; начата реализация backend/frontend/migration.
- `2026-03-11` — `P0` полностью закрыт: `P0-1..P0-6 = DONE`, миграция применена, backfill и API smoke-check пройдены.
- `2026-03-11` — выявлен отдельный технический долг вне `P0`: рассинхрон ORM/DB по `custom_field_values.created_at` (не блокирует `P0`, требует отдельной миграции/выравнивания модели).
- `2026-03-11` — стартован `F8` (compact UI): обновлены `Leads` и визуальная плотность `Pipeline`, зафиксирован стандарт компактного интерфейса с Tabler icons как часть production readiness.
- `2026-03-11` — `F8` расширен: внедрен референсный account dropdown в Topbar (`My account` / `Company overview`) с permission-aware пунктами (`Profile`, `Settings`, `Users`, `Billing`, `Tools`).
- `2026-03-11` — `F8` расширен на все страницы настроек: в `AppShell` добавлен общий `SettingsChrome` (единая шапка + навигация по зонам ответственности) и единый `settings-surface` стиль для консистентного UI.
- `2026-03-11` — `F8` второй проход для `settings/*`: унифицирована внутренняя плотность контента (формы/таблицы/секции) через общий CSS-стандарт, выровнены страницы с локальными отступами (`Funnels`, `CandidateProfiles`, `CustomFields`).
- `2026-03-11` — `F8` расширен до глобального стандарта UI: внедрен общий слой `app-ui` для всех страниц (типографика, формы, кнопки, таблицы, секции, отступы), подключенный на уровне `AppShell`.
- `2026-03-11` — выполнен глобальный visual-pass по страницам и навигации: палитра приведена к единому `slate/brand` стандарту, выровнены базовые интервалы (`space-y-4`), подтверждена сборкой frontend.
- `2026-03-11` — финальный технический pass по всему `hostflow-frontend/src/*.tsx`: остатки `gray-*` и `space-y-6` сведены к `0`, сборка frontend проходит; визуальная консистентность приведена к единому стандарту.
- `2026-03-11` — точечный UX-fix после визуального ревью: исправлен hero блока `VacancyDetail` (убран double-pill эффект stage chips, action buttons приведены к компактному стандарту).
- `2026-03-11` — дополнительный UI-fix после QA: починены table header controls в `DoProcesowania`, заменены legacy emoji/old-icons на Tabler в `CandidateCard`/`Candidates`/`Pipeline` и секциях карточки кандидата.
- `2026-03-11` — `F8.11 = DONE`: остаточные локальные error-state блоки унифицированы (`Pipeline`, `DocumentsRegistry`, `CommunicationsCommandAudit`, `ClientPortal`) на общий `ErrorRecoveryBanner` с `Retry`.
- `2026-03-11` — `F8.12 = DONE`: выровнены destructive-кнопки и локальные error-блоки (`VacancyList`, `ClientLinkDetail`, `VacancyDetail`, `Companies`, `CandidateProfiles`, `CustomFields`) под единый системный UI (`ErrorRecoveryBanner`, `btn-danger`).
- `2026-03-11` — `F8.13 = DONE`: закрыты остаточные legacy action-controls (`btn-outline` и link-style действия) в `Dashboard`, `ClientLinkDetail`, `AgencyClients`, `Profile`, `MetaLeadsAdmin`; действия переведены на `btn-secondary/btn-danger`.
- `2026-03-11` — `F8.14 = DONE`: `RulesetVersions`, `Invoices`, `OnboardingCompany`, `Candidates` очищены от остаточных legacy red-state/action-patterns и приведены к системным `ErrorRecoveryBanner`/`btn-secondary`/`btn-danger`.
- `2026-03-11` — `F8.15 = DONE`: внутренние формы и карточки CRM (`UserFormCreate`, `UserFormInvite`, `CandidateHeader`, `CandidateRodoSection`, `ServicesPage`, `CommunicationsEmailInbox`) доведены до единого системного паттерна ошибок и destructive-actions.
- `2026-03-11` — `F8.16 = DONE`: конструкторы профилей и блок messenger templates (`ProfileDocumentConstructor`, `ProfileFieldConstructor`, `StageConstructor`, `CommunicationsMessengerSettingsPage`) выровнены под системные `btn-secondary/btn-danger`.
- `2026-03-11` — `F8.17 = DONE`: коммуникационные рабочие экраны (`CommunicationsCommandAuditPage`, `CommunicationsPlannerPage`, `TimeOffRequestsPage`) выровнены по системным control-классам и action-patterns.
- `2026-03-11` — `F8.18 = DONE`: `CommunicationsEmailInboxPage` полностью переведен на системные control/action классы; локальные ручные `rounded border ...` стили убраны из основных рабочих секций.
- `2026-03-11` — `F8.19 = DONE`: `CommunicationsQueueSettingsPage` и `CommunicationsSlaSettingsPage` доведены до системного UI-контурa (controls + save notices).
- `2026-03-11` — `F8.20 = DONE`: `CommunicationsMessengerSettingsPage` приведен к системным control/action классам; устранены локальные стили в формах каналов и шаблонных блоках.
- `2026-03-11` — `F8.21 = DONE`: `CommunicationsSetupPage` доведен до системного UI для action/notice элементов (`btn-secondary` для next-step, `alert-success` для operation notice), локальные ad-hoc стили убраны.
- `2026-03-11` — `F8.22 = DONE`: закрыты остаточные legacy controls на коммуникационных экранах (`CommunicationsThreadPage`, `CommunicationsMessengerSettingsPage`) с переводом на системные `btn-secondary`/`alert-success` и упрощением checkbox-label UI.
- `2026-03-11` — `F8.23 = DONE`: `CommunicationsMessagesPage` выровнен по системной UI-библиотеке controls/actions; локальные `rounded border ...` классы убраны из ключевых интерактивных зон (toolbar, manager/tags/candidate tools, compose, modals).
- `2026-03-11` — `F8.24 = DONE`: `CommunicationsCalendarPage` выровнен по системным control/action классам в основных пользовательских потоках (filters, batch-actions, quick-actions, create forms, planner/reminders links).
- `2026-03-11` — `F8.25 = DONE`: закрыт второй проход по `CommunicationsCalendarPage` — динамические `clsx` controls переведены на системные `btn-*` классы с сохранением состояния `active/selected`.
- `2026-03-11` — `F8.26 = DONE`: закрыт точечный pass по коммуникационным остаткам (`CommunicationsMessagesPage`, `CommunicationsMessengerSettingsPage`, `CommunicationsThreadPage`) с переводом динамических controls на системные `btn-*`/`badge`.
- `2026-03-11` — `F8.27 = DONE`: унифицированы статусные чипы в `CommunicationsCalendarPage` через единый `badge` паттерн (счетчики дней, now-marker, source/status/priority/tags).
- `2026-03-11` — `F8.28 = DONE`: `CommunicationsThreadPage` и `CommunicationsSlaIncidentsPage` доведены до системного control/action паттерна (`btn-secondary`, `dropdown-item`, `input`, `btn-secondary btn-xs`).
- `2026-03-12` — `F8.29 = DONE`: action-меню `CommunicationsMessagesPage` (`workflow/sla/more`) переведены на системный `dropdown-item`, локальные menu-item классы убраны.
- `2026-03-12` — `F8.30 = DONE`: `CommunicationsEmailInboxPage` приведен к системному паттерну folder-controls и tag chips (`btn-secondary` + `badge`).
- `2026-03-12` — `F8.31 = DONE`: `CommunicationsCalendarPage` event pills/cards выровнены на системные базы (`badge border`, `rounded-lg`), локальные legacy pill-классы убраны.
- `2026-03-12` — `F8.32 = DONE`: введен системный `alert-info` и применен в communication info/checklist блоках (`CommunicationsMessagesPage`, `CommunicationsMessengerSettingsPage`) вместо локальных cyan alert-стилей.
- `2026-03-12` — `F8.33 = DONE`: завершен micro-polish коммуникационного UI (focus-ring для channel cards + `rounded-lg` month day-cells в calendar) для финальной визуальной консистентности.
- `2026-03-12` — `F8.34 = DONE`: завершена унификация акцентного цвета в communications workflow views (active/filter/selected states и индикаторы переведены с `cyan` на `brand` palette).
- `2026-03-12` — `F8.35 = DONE`: закрыты остаточные color/control выбросы в communications pages (system `alert-info` и `brand` accent в messenger checklist summary, SLA include-read checkbox, calendar info alert, outbound message meta text).
- `2026-03-12` — `F8.36 = DONE`: закрыт пакет базовой стандартизации controls (`input/textarea` в thread compose, `brand` progress bar в setup, `badge` для date divider в messages).
- `2026-03-12` — `F8.37 = DONE`: auxiliary chips/empty-state элементы в communications pages приведены к системному паттерну (`badge`, `rounded-lg` dashed empty blocks).
- `2026-03-12` — `F8.38 = DONE`: `CommunicationsSetupPage` доведен до brand-consistent визуального паттерна (focus-ring, hero gradient, status chips).
- `2026-03-12` — `F8.39 = DONE`: secondary badges/cards в communications views выровнены на системный паттерн (`badge`, `rounded-lg`) в `CommunicationsSlaIncidentsPage`, `CommunicationsMessagesPage`, `CommunicationsCalendarPage`.
- `2026-03-12` — `F8.40 = DONE`: `CandidateCommunicationSection` и quick-controls в `CandidateCard` переведены на системные `brand/btn-secondary/alert-info` паттерны; `StageTag` для ключевых этапов коммуникации выровнен под единый `brand` accent.
- `2026-03-12` — `F8.41 = DONE`: `ServicesPage` (catalog + new order + order detail) переведен с локальных `rounded border ...` controls на системные `input/textarea/btn-primary/btn-secondary`; выбранные owner-блоки унифицированы через `alert-info`, исправлена опечатка layout-класса.
- `2026-03-12` — `F8.42 = DONE`: `MyAvailabilityPage` переведен с локальных `rounded border ...` controls/actions на системные `input/textarea/btn-primary/btn-secondary` (форма, cancel-action, quick-links).
- `2026-03-12` — `F8.43 = DONE`: `RulesetVersionsPage` переведен на системные controls/actions (`textarea`, `input`, `btn-primary`, `btn-secondary`, `badge`), diff-секции и active-row выровнены под единый `slate/brand` стиль.
- `2026-03-12` — `F8.44 = DONE`: `AgencyClientsPage` переведен на системные `input/btn-secondary/badge` для portal-link input/actions, edit-action, modal inputs и статусных чипов.
- `2026-03-12` — `F8.45 = DONE`: `ProfilePage` выровнен по системным action/status patterns (`btn-secondary` для saved-view actions, `badge` для статусных маркеров, `alert-success/alert-error` для локальных уведомлений).
- `2026-03-12` — `F8.46 = DONE`: `BillingTeamPage` выровнен по системным seat-request patterns (`btn-secondary btn-xs`, `textarea`, `alert-error`, `badge`) в refresh/form/status блоках.
- `2026-03-12` — `F8.47 = DONE`: `UsersPage` очищен от `btn-ghost` в ключевых вторичных действиях (detail, audit, tenant override, list refresh), применен единый `btn-secondary` паттерн.
- `2026-03-12` — `F8.48 = DONE`: `TenantsPage` очищен от остаточных `btn-ghost` в admin access flows (seat requests, vacancy sharing, module user overrides), применен системный `btn-secondary` паттерн.
- `2026-03-12` — `F8.49 = DONE`: `MetaLeadsAdminPage` выровнен по системным controls/actions (`btn-primary/btn-secondary/input/textarea`), success notice переведен на `alert-success`, logs/modal actions унифицированы.
- `2026-03-12` — `F8.50 = DONE`: в `MetaLeadsAdminPage` mapping form/search controls переведены на системные `input`/`btn-primary`; ad-hoc `rounded border ...` поля для `ad_id/vacancy_id/note/search` убраны.
- `2026-03-12` — `F8.51 = DONE`: `AuditLogPage` tabs/refresh/pagination actions выровнены на системный `btn-primary/btn-secondary btn-sm` паттерн, ad-hoc tab styles и `btn-ghost` убраны.
- `2026-03-12` — `F8.52 = DONE`: `LegalDocumentsPage` cleanup secondary actions — кнопки `cancel` и `add version` переведены с `btn-ghost` на системные `btn-secondary`/`btn-secondary btn-sm`.
- `2026-03-12` — `F8.53 = DONE`: пакетная унификация secondary actions в admin-экранах (`CandidateProfiles`, `CompanyAccess`, `DeletionRequests`, `CustomFields`, `TenantLinksSettings`) — `btn-ghost`/link-style кнопки переведены на `btn-secondary` (`btn-sm/btn-xs`).
- `2026-03-12` — `F8.54 = DONE`: пакетная унификация secondary actions в `DoProcesowaniaPage`, `DocumentsRegistryPage`, `AgencyClientsPage` — остаточные `btn-ghost` (CSV/filter reset/modals/pagination/advanced toggle) переведены на `btn-secondary`.
- `2026-03-12` — `F8.55 = DONE`: пакетная унификация secondary actions в `VacancyForm`, `VacancyDetail`, `CandidateCard`, `ClientInvoicesBlock` — модальные/карточные `btn-ghost` действия переведены на `btn-secondary`.
- `2026-03-12` — `F8.56 = DONE`: пакетная унификация secondary actions в candidate bulk-модалках (`BulkManager/Handoff/Tags/Vacancy/Delete/Stage`) — `btn-ghost` cancel/actions переведены на `btn-secondary`.
- `2026-03-12` — `F8.57 = DONE`: пакетная унификация controls в candidate секциях (`Notes/Reminders/ContactAttempts/Basic/Experience/Handoff`) — `btn-ghost` заменены на `btn-secondary`, удаление строки опыта переведено на `btn-danger`.
- `2026-03-12` — `F8.58 = DONE`: `CandidatesPage` очищен от остаточных `btn-ghost` в фильтрах/menus/save-view/saved-views; применен единый `btn-secondary` паттерн для вторичных действий.
- `2026-03-12` — `F8.59 = DONE`: `RemindersPage` очищен от `btn-ghost` в quick compose/filters/task-event actions/edit modal; применен единый `btn-secondary` паттерн.
- `2026-03-12` — `F8.60 = DONE`: крупный пакет по shared workspace views — `Pipeline`, `Dashboard`, `Topbar`, `UserTable`, `ColumnFilterMenu`, `DocumentWorkflow`, `DocumentCard` переведены с `btn-ghost` на системные `btn-secondary`; reject/delete в документах выровнены на `btn-danger`.
- `2026-03-12` — `F8.61 = DONE`: `CompaniesPage` (detail + list + embedded forms) очищен от `btn-ghost`; вторичные действия переведены на `btn-secondary`, destructive remove/delete/archive — на `btn-danger` (restore оставлен как `btn-secondary`).
- `2026-03-12` — `F8.62 = DONE`: после закрытия миграции удален legacy-класс `.btn-ghost` из `components.css`; подтверждено отсутствие `btn-ghost` usage в `hostflow-frontend/src`.
- `2026-03-12` — обновлен рабочий git-регламент для `F8`: пакетные изменения/commit/build, единый логический трек задачи и обязательный cleanup промежуточных веток после завершения `F8`.
- `2026-03-12` — в SSOT добавлены отдельные обязательные направления: `SEO technical`, `SEO content rollout` и `Mobile adaptation pass` (критерии `36–38`, задачи `F9/F10/F11`).
- `2026-03-12` — детализированы треки `F9/F10/F11`: добавлена подзадачная декомпозиция с измеримыми DOD для technical SEO, content rollout и mobile QA-pass.
- `2026-03-12` — для `F11` добавлены baseline mobile QA matrix (по ключевым route/экранам) и первичный bug backlog `MOB-001..003` с severity/owner/triage-правилом.
- `2026-03-12` — `MOB-001 = DONE`: в `Topbar` profile dropdown переведен с фиксированной ширины `w-[320px]` на адаптивную `w-[min(96vw,320px)]` для экранов `320px`.
- `2026-03-12` — `MOB-002 = DONE`: `Pipeline` side panel сделан адаптивным (`w-full sm:w-96`, корректный main-content offset), что убирает mobile-overlap на узких экранах.
- `2026-03-12` — `Pipeline` исправлен по видимости этапов: в kanban-грид добавлено объединение `data.statuses + columnOrder + stage_columns`, а в заголовках колонок отображается полный список stage codes внутри колонки.
- `2026-03-12` — `MOB-003 = DONE`: comparison-блок на CRM landing адаптирован под mobile (карточки без горизонтального скролла на `<md`, таблица оставлена для `md+`).
- `2026-03-12` — `MOB-004 = DONE`: внедрен системный mobile touch baseline для модалок (`modal-surface`: `min-h-[44px]` для controls + мобильный `max-h`/scroll в `Modal`), стартован `F11.4` audit snapshot.
- `2026-03-12` — расширен `F11.4` audit: добавлен global touch baseline для `btn/input/dropdown-item` и зафиксирована CRUD matrix (`Candidates/Clients/Leads/Settings`) с `PASS` по `320/375/390/768` на уровне статического touch-аудита.
- `2026-03-12` — `F11` синхронизирован до release-report v1: `F11.2/F11.3 = DONE`, добавлена пометка `PASS_STATIC` по матрице и раздел `5.6.8` с residual risks и decision `GO_WITH_MANUAL_QA_PENDING`.
- `2026-03-12` — добавлен `Sales Unblock Execution Pack` (раздел `5.1.1`) с пошаговым планом `S1..S5` для снятия блока `A1/A2` и формального выхода на release-gate `A5`.
- `2026-03-12` — закрыт signup/onboarding hotfix: принудительный auth-refresh после login на `/signup`, добавлен явный post-signup trial-success banner на onboarding, исправлен маршрут шага `services` (`/app/clients`), добавлены legacy redirects `/app/companies* -> /app/clients*`.
- `2026-03-12` — усилен post-signup recovery path: signup success context (`trial/email`) дублируется в `sessionStorage` и читается в `OnboardingCompanyPage` как fallback, чтобы success/trial/legal блок не терялся при race-редиректе на `/app/overview`.
- `2026-03-12` — убран post-signup redirect тупик: для авторизованного пользователя маршрут `/signup` теперь проверяет `signup success context` и направляет в `/app/onboarding/company` (с сохранением `signup/welcome_email/trial_ends_at`), а не всегда в `/app/overview`.
- `2026-03-12` — invite recovery UX доработан: после успешного `invite accept` при неудачном auto-login пользователь переводится на `/login` с явным notice (`Invitation accepted`) и prefilled email, чтобы исключить ложный сигнал об ошибке.
- `2026-03-12` — session-expiry routing fix: для `!me` добавлен явный редирект `/app/* -> /login` (вместо попадания в public `404`), чтобы recovery path после истечения токена был однозначным.
- `2026-03-12` — password reset recovery UX доработан: после успешного `reset-with-token` перед редиректом на `/login` сохраняется notice (`Password updated`), и на login показывается явное подтверждение завершения сценария.
- `2026-03-12` — auth refresh hardening: `AuthProvider` переведен на path-aware логику через `useLocation` (вместо одноразового `window.location` snapshot), чтобы переход `public -> /app` корректно инициировал `refresh()` и не приводил к ложному `unauth` состоянию.
- `2026-03-12` — `E4 = DONE`: закрыт пакет auth hardening для self-serve (`signup`, `invite accept`, `session expiry`, `password reset`, `public->app refresh`) с явными recovery notices и route-level fallback.
- `2026-03-12` — auth recovery stabilization: login notices (`expired`, `invite_accepted`, `password_reset_success`) централизованы в `store/auth` (`remember/consume` helpers), страницы `Login/InviteAccept/ResetPassword` переведены на единый механизм без дублирования `sessionStorage` логики.
- `2026-03-12` — расширен self-serve signup информационный контур: добавлены legal links на `/signup` и onboarding success, backend welcome email с trial/policy/billing ссылками, в topbar внедрен постоянный `Trial` badge (пока tenant в статусе `trial`).
- `2026-03-12` — добавлен `Trial Center` banner на `Dashboard`: для tenant в статусе `trial` отображаются статус/остаток дней (если доступен), legal links и CTA в `Billing`.
- `2026-03-12` — усилен legal-consent на self-serve signup: добавлены обязательные чекбоксы `Terms`/`Privacy` в форме регистрации и backend-валидация с записью `signup_consents` (`accepted_at`, версии документов) в `user.extra`.
- `2026-03-12` — добавлена прозрачность доставки welcome email: `/auth/register` возвращает `meta.welcome_email_sent`, а onboarding success показывает статус (`sent/not_sent`) с fallback на `Billing`.
- `2026-03-12` — добавлен API test coverage для self-serve signup (`backend/tests/api/test_auth_register.py`): проверка mandatory consent и сохранения `signup_consents` + `meta.welcome_email_sent`.
- `2026-03-12` — усилена прозрачность trial в `BillingWorkspacePage`: добавлен `Trial status` banner с urgency-эскалацией (`<=7` warning, `<=2` critical), CTA `Upgrade now`, ссылками на legal docs и next-step переходом к onboarding (`Continue setup`).
- `2026-03-12` — локализованы тексты `Billing trial` блока (`app.settings.billing.trial.*`) для `en/ru/pl`; `i18n:check` подтверждает синхронизацию словарей.
- `2026-03-12` — добавлен глобальный `Trial status` banner в `AppShell`: отображается на всех внутренних экранах для tenant со статусом `trial`, показывает urgency по остатку дней, legal links и role-aware CTA (`Open billing` для админов, fallback в `Overview` для остальных).
- `2026-03-12` — исправлен activation redirect-loop в `AppShell`: при `activation_required=true` разрешены рабочие маршруты шагов (`/app/clients`, `/app/vacancies`, `/app/leads`, `/app/reminders`, `settings/billing`, `settings/legal`), поэтому CTA в `OnboardingGettingStartedPage` больше не “застревают” на той же странице.
- `2026-03-12` — `OnboardingGettingStartedPage` сделан permission-aware: CTA шагов проверяют доступ роли к целевому разделу и при отсутствии прав ведут в `Dashboard` с явным fallback-label вместо “немого” перехода в недоступный route.
- `2026-03-12` — старт `F9.3`: добавлены `public/robots.txt` (disallow для `/app` и tokenized public URLs) и `public/sitemap.xml` с базовым перечнем indexable страниц (`/, /pricing, /signup, /login, /public/intake, /public/portal, legal pages`); статус `F9.3` переведен в `IN_PROGRESS` до внедрения auto-generation.
- `2026-03-12` — `F9.1 = DONE`: зафиксирован baseline SEO URL inventory (`indexable`/`non-indexable`) с owner-матрицей в разделе `5.6.1.1`.
- `2026-03-12` — `F9.2 = DONE`: внедрен единый SPA SEO-хук (`title`, `description`, `canonical`, `og:title`, `og:description`, `og:type`, `og:url`, `og:site_name`) и подключен на indexable public/auth страницах (`/`, `/pricing`, `/signup`, `/login`, `/public/intake`, `/public/portal`) с локализацией `app.seo.*` для `en/ru/pl`.
- `2026-03-12` — старт `F9.4`: SEO-хук расширен поддержкой JSON-LD (`application/ld+json`), на `CRM landing/pricing` добавлены schema.org `Organization` + `SoftwareApplication`; статус `F9.4` переведен в `IN_PROGRESS` до расширения на FAQ/контентные страницы и внешней валидации.
- `2026-03-12` — `F9.4 = DONE`: structured data расширен до `FAQPage` (JSON-LD из фактического FAQ блока CRM landing), что закрывает baseline-покрытие `Organization + SoftwareApplication + FAQ`.
- `2026-03-12` — `F9.5 = DONE`: завершен crawlability baseline (robots + noindex-map + anti-soft-404 route handling + audit snapshot). Остается non-blocking residual risk: server-level HTTP `404` policy для SPA-hosting.
- `2026-03-12` — старт `F9.6`: внедрен CWV-baseline micro-pass для public surfaces (dns-prefetch к font origins в `index.html`, LCP-hint для hero media на `/public/portal` через `loading=eager` + `fetchPriority=high`); статус `F9.6` переведен в `IN_PROGRESS`.
- `2026-03-12` — расширен `F9.6`: включен lazy route code-splitting для тяжелых public flows (`/public/apply*`, `/public/status/:token`, `/public/scan`, `/client-portal`), что вынесло их в отдельные чанки (`~4–109KB`) и снизило основной `index` bundle до `~5.23MB` (по build snapshot).
- `2026-03-12` — расширен `F9.6`: для секций ниже первого экрана в `CRM landing` и `Public portal` включен render deferral (`content-visibility:auto`, utility `.cv-auto`) для снижения initial render cost.
- `2026-03-12` — `F9.3 = DONE`: добавлена автогенерация sitemap (`scripts/generate-sitemap.mjs`) и подключение в `prebuild`, что гарантирует актуальный `public/sitemap.xml` на каждом production build.
- `2026-03-12` — `F9.6 = DONE`: завершен baseline CWV pass (font/network hints, LCP media priority, lazy route splitting, below-the-fold render deferral) с фиксацией static snapshot и residual monitoring риска.
- `2026-03-12` — `F10.1 = DONE`: зафиксирована keyword-intent карта (`landing/pricing/feature/use-case/comparison`) и приоритизированный content backlog `Wave-1/Wave-2`; статус направления `F10` переведен в `IN_PROGRESS`.
- `2026-03-12` — `F10.2 = DONE`: сформирован единый SEO content template pack (`docs/seo/content-page-template.md`) с обязательной структурой блоков/CTA/internal links/FAQ/schema и baseline tracking требованиями для wave-публикаций.
- `2026-03-12` — `F10.3 = DONE`: выпущен wave-1 контент-пакет (`/features/candidate-pipeline`, `/features/document-control`, `/use-cases/trucking-recruitment`, `/use-cases/high-volume-onboarding`) с SEO metadata + FAQ schema + dual CTA.
- `2026-03-12` — `F10.4 = DONE`: реализована внутренняя перелинковка между landing/features/use-cases; в landing добавлен guide-hub блок, sitemap auto-generation расширен до новых wave-1 URL.
- `2026-03-12` — `F10.5 = DONE`: подключен baseline conversion tracking для SEO-контента (`seo_cta_click`, `seo_scroll_depth`) через `window.dataLayer` на landing и всех wave-1 страницах.
- `2026-03-12` — направления `F9` и `F10` синхронизированы в общий `DONE` статус (включая критерии `36/37`); зафиксированы остаточные non-blocking риски по continuous monitoring и server-level `404` policy для SPA-hosting.
- `2026-03-12` — расширен content rollout после закрытия `F10`: опубликованы comparison-страницы (`/comparison/hostflow-vs-spreadsheets`, `/comparison/recruitment-crm-vs-ats`) с SEO metadata/FAQ schema/tracking и включены в route map + auto-sitemap + landing guide links.
- `2026-03-12` — старт `F9.5`: внедрен управляемый `robots` meta для crawlability (глобальный `noindex,nofollow` в `/app/*` + tokenized/public private routes), а для indexable страниц `useSeoMeta` принудительно устанавливает `index,follow` для корректного SPA-переопределения при навигации.
- `2026-03-12` — расширен `F9.5` на auth-utility страницы: `Forgot password`, `Reset password`, `Invite accept` помечены как `noindex,nofollow` для исключения нецелевых service URL из выдачи.
- `2026-03-12` — `F9.5` дополнен anti-soft-404 фиксом: неизвестные public URL больше не редиректятся на home, а открывают `PublicNotFoundPage` с `noindex,nofollow`; добавлен crawlability audit snapshot (`5.6.1.2`) и зафиксирован residual risk server-level `HTTP 404` policy для SPA-hosting.
- `2026-03-12` — старт `F5` lifecycle retention path: в `Dashboard` добавлены trial in-app nudges по day-buckets `D1/D3/D7` с context-aware CTA на следующий onboarding шаг и tenant/day-scoped dismiss persistence; критерий `#25` переведен в `IN_PROGRESS`.
- `2026-03-12` — расширен `F5` lifecycle retention path: добавлен day-bucket `D2` и baseline analytics events (`trial_retention_nudge`: `impression/cta_click/dismiss`) через `window.dataLayer`.
- `2026-03-12` — завершен `F5`: добавлен backend-контур retention analytics (`POST /analytics/events`, `GET /analytics/trial-retention`) на базе `activity_log`, а в `Dashboard -> Trial Center` выведен day-level отчет `D1/D2/D3/D7` (impressions/clicks/dismiss/CTR); критерий `#25` переведен в `DONE`.
- `2026-03-12` — старт `F6` terminology unification wave-1: в `Dashboard` убран конфликт `Clients / Companies`, введены business-aware entity labels (`Client/Company` по типу бизнеса), а в `AgencyClientsPage` empty-state CTA выровнен на `Open clients`; добавлен snapshot `5.6.10`.
- `2026-03-12` — для `F6` добавлен canonical словарь `docs/ux/business-terminology-map.md` с правилами использования терминов по типам бизнеса (`agency/employer/services`) и wave scope (`wave-1/wave-2`).
- `2026-03-12` — `F6` wave-2: business-aware термин `Clients/Companies` применен в `Sidebar`, `Topbar` quick targets и `Breadcrumbs` для `/app/clients` (вместо единого статического label).
- `2026-03-12` — `F6` расширен на secondary screens: добавлен общий `useBusinessTerminology` hook; `LeadsPage`/`ServicesPage` используют business-aware CTA/labels для перехода в `/app/clients` (`Open clients` vs `Open companies`).
- `2026-03-12` — `F6` расширен на onboarding copy-pass: `OnboardingGettingStartedPage` и `OnboardingWizard` используют business-aware CTA для `/app/clients` (`Open clients` / `Open companies`); `OnboardingGettingStartedPage` добавляет динамический entity-термин для сервисного шага (`Create first client/company`).
- `2026-03-12` — anti-dead-end UX pass для onboarding activation: в `OnboardingGettingStartedPage` карточки шагов сделаны полностью кликабельными (мышь/клавиатура), чтобы переход в целевой раздел не зависел только от маленькой inline-ссылки.
- `2026-03-12` — `F6` secondary-screen copy-pass расширен на `ClientLinkDetailPage`: ссылка «back to list» для `/app/clients` теперь business-aware (`Back to clients` / `Back to companies`) по типу бизнеса.
- `2026-03-12` — `F6` secondary-screen copy-pass в `ClientLinkDetailPage` дополнен dynamic not-found copy: заголовок ошибки теперь формируется по entity-term (`Client/Company not found`) в зависимости от типа бизнеса.
- `2026-03-12` — `F6` secondary-screen copy-pass расширен на `AgencyClientsPage`: secondary empty-state CTA на `/app/clients` переведен на `useBusinessTerminology.openEntityLabel` (`Open clients` / `Open companies`).
- `2026-03-12` — `F6` расширен в `AgencyClientsPage` на heading/empty-state primary CTA: title/subtitle и `Add ...` action теперь используют business-aware entity terms (`Client/Company`) через `useBusinessTerminology`.
- `2026-03-12` — `F6` расширен в `AgencyClientsPage` на add-link modal: modal title и `display name` label переведены на dynamic entity-term (`client/company`) через `useBusinessTerminology`.
- `2026-03-12` — `F6 = DONE`: финальный secondary-screen copy-pass завершен (включая dynamic empty-title и success toast в `AgencyClientsPage`), конфликтующих `client/company` терминов в user-facing CTA/headers не осталось.
- `2026-03-12` — `F7` execution board обновлен: добавлен формальный протокол прогона (`docs/manual-checklist/f7-scenario-protocol.md`), зафиксирован текущий state (`A=BLOCKED` по Stripe, `B/C=IN_PROGRESS` с `PASS_STATIC` как промежуточный code/UI результат до ручного sign-off).
- `2026-03-12` — `F7` execution board переведен в операционный формат: добавлен run-log `10.1` (дата/окружение/tenant/result/evidence/owner) и зафиксированы next actions `10.2` для последовательного закрытия `B/C` и снятия блокера `A`.
- `2026-03-12` — для `F7` добавлены отдельные run-sheets сценариев `B/C` (`docs/manual-checklist/f7-scenario-b-agency.md`, `docs/manual-checklist/f7-scenario-c-employer.md`) и привязаны к шагам `10.2`.
