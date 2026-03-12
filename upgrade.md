ТЗ HostFlow: RODO + Handoff + Processor + Контактные попытки + Нормализация данных (версия 1.0)

Цель

Сделать юридически корректный и операционно управляемый процесс:
	1.	Кандидат всегда проинформирован по RODO:

	•	через твою анкету (checkbox до отправки),
	•	через FB-лиды (email RODO при первом контакте, с логом).

	2.	Чёткая ответственность:

	•	до передачи (handoff) — агентство отвечает и редактирует,
	•	после принятия (handoff accepted) — клиент отвечает и редактирует,
	•	возврат возможен только явным действием (return).

	3.	Разделение ролей:

	•	manager (агентство) — для аналитики, не меняется,
	•	processor (клиент) — отвечает за операционную обработку после передачи.

	4.	Контактные попытки:

	•	до 3 попыток,
	•	после 3-й неудачи — финальное сообщение и авто-отклонение “не отвечает”.

	5.	Нормализация стран/городов:

	•	латиница в отображении,
	•	хранение оригинала,
	•	исключение “кириллица в полях, которые клиент читает”.

⸻

0. Термины и принципы
	•	Candidate — карточка кандидата в ATS.
	•	Manager — агентский ответственный (рекрутер агентства). Не меняется при передаче.
	•	Client tenant — тенант работодателя (например, Citronex Trans Logistic).
	•	Processor — пользователь со стороны клиента, который ведёт кандидата после принятия.
	•	Handoff — механизм передачи кандидата клиенту (не статус и не этап).
	•	Immutable event — событие, которое нельзя “переотметить” и изменить задним числом.

Канон:
	•	Этапы остаются настраиваемыми и не определяют ответственность.
	•	Ответственность определяется только handoff-событиями и ACL.

⸻

1. Роли и доступы (RBAC/ACL)

1.2 Роли в клиентском тенанте (Client)
	•	client_admin
	•	client_recruiter — создаёт “своих” кандидатов
	•	client_processor — принимает/отклоняет и ведёт кандидатов агентства
	•	client_viewer — read-only

Один пользователь может иметь несколько ролей.

⸻

1.3 Доступ к кандидату по состоянию передачи

До handoff (нет принятой передачи)

Agency:
	•	edit: да
	•	stage move: да
	•	docs: да
	•	send RODO: да
	•	log contact attempts: да

Client:
	•	view: да (если кандидат связан с этим клиентом/вакансией или вручную “шарен”)
	•	edit: нет
	•	stage move: нет
	•	accept/reject: да (только если есть pending handoff)

После handoff accepted

Client:
	•	edit: да
	•	stage move: да (по их этапам)
	•	assign processor: да
	•	docs: да

Agency:
	•	view: да
	•	edit: нет
	•	stage move: нет
	•	docs edit: нет (read-only)

Возврат (handoff returned)

Возвращает права агентству, клиент — снова read-only.

⸻

2. Handoff: передача кандидата клиенту

2.1 Сущность candidate_handoffs

Поля:
	•	id (uuid)
	•	candidate_id
	•	from_tenant_id (agency)
	•	to_tenant_id (client)
	•	requested_by_user_id
	•	requested_at (UTC)
	•	assigned_to_user_id (nullable) — если при передаче назначаем конкретного процессора/проверяющего
	•	status enum: pending_review | accepted | rejected | returned | cancelled
	•	reviewed_by_user_id (nullable)
	•	reviewed_at (nullable)
	•	rejection_reason (text, required if rejected)
	•	return_reason (text, required if returned)
	•	meta jsonb (опц.: vacancy_id, campaign_id и т.д.)

Ограничения:
	•	одновременно может быть только один active handoff в статусе pending_review для пары (candidate, client).
	•	immutable audit: любые изменения статуса пишутся отдельными событиями (см. лог).

⸻

2.2 UI/UX: действие агентства

Кнопка в карточке кандидата + массово в таблице:

Przekaż do klienta

Диалог:
	•	Client (обязательно, если не задан через vacancy)
	•	Assign to (опционально: конкретный processor; иначе — в общий inbox)

Результат:
	•	создаётся handoff со статусом pending_review
	•	клиент видит кандидата в очереди Do procesowania

⸻

2.3 UI/UX: действие клиента

Экран: Do procesowania (Inbox)
Фильтр: handoff.status = pending_review для данного клиента.

Действия:
	1.	Przyjmij
	•	handoff.status = accepted
	•	reviewed_by_user_id = current_user
	•	если assigned_to_user_id пустой → ставим assigned_to_user_id = current_user как processor по умолчанию
	•	создаём связь processor в участниках (см. 3.1)
	2.	Odrzuć
	•	обязательный rejection_reason
	•	handoff.status = rejected
	•	уведомление агентству + причина
	3.	Zwróć do agencji (только после accepted)
	•	обязательный return_reason
	•	handoff.status = returned
	•	снимаются права клиента на редактирование, агентство снова edit

⸻

3. Processor и участники кандидата

3.1 Сущность candidate_participants (универсально, масштабируемо)

Поля:
	•	id
	•	candidate_id
	•	tenant_id
	•	user_id
	•	role enum: owner | manager | processor | viewer
	•	active bool
	•	created_at

Правила:
	•	manager существует только у agency tenant (или роли agency user).
	•	processor создаётся/активируется только после handoff.accepted.
	•	можно иметь несколько processors (опц.), но один primary_processor (см. ниже).

3.2 Primary processor (если нужно)

Вариант А (через таблицу participants):
	•	добавляем поле is_primary bool, уникальность (candidate_id, tenant_id, role=processor, is_primary=true).

Вариант B:
	•	в candidate_handoffs.assigned_to_user_id считаем primary processor для клиента.

Рекомендация: B, проще и достаточно для 1.0.

⸻

4. RODO-информирование: форма и FB-лиды

4.1 Legal documents

Сущность legal_documents
	•	id
	•	tenant_id (agency tenant)
	•	type enum: rodo_clause | privacy_policy
	•	version_id (строка/uuid)
	•	content_html или content_url
	•	published_at
	•	is_active

Правило:
	•	всегда есть одна активная версия по типу.

⸻

4.2 Канал 1: твоя анкета (public form)

Требования:
	•	до submit обязательный checkbox:
	•	текст конфигурируемый
	•	ссылки на активные версии документов
	•	запись согласия:
	•	candidate_consents (или lead_consents, если лид создаётся отдельно)
	•	фиксируем: given_at, ip, user_agent, rodo_version_id, privacy_version_id, source=public_form

⸻

4.3 Канал 2: FB Lead Ads — обязательный второй шаг (art.14)

Требования:
	•	при первом контакте кандидат получает email с инфо + ссылкой на klauzula.
	•	это фиксируется как immutable event.

UI в карточке кандидата

Блок RODO
	•	Кнопка: Wyślij informację RODO (активна, если ещё не отправлено и есть email)
	•	После отправки:
	•	отображаем sent_at, sent_by, to_email, rodo_version_id
	•	кнопка disabled (повторная отправка только админом через отдельную “resend” с отдельным событием, см. ниже)

⸻

4.4 Сущность/лог: rodo_notifications

Вариант A: отдельная таблица
	•	id
	•	candidate_id
	•	sent_at
	•	sent_by_user_id
	•	channel enum: email | sms | whatsapp
	•	recipient (email/phone)
	•	rodo_version_id
	•	status enum: sent | failed
	•	provider_message_id (если есть)

Правила:
	•	Первая успешная отправка закрывает “obowiązek informacyjny”.
	•	Повторная отправка допускается только через отдельное действие Resend, создающее новую запись, не меняя первую.

⸻

5. Контактные попытки: максимум 3

5.1 Сущность contact_attempts

Поля:
	•	id
	•	candidate_id
	•	attempt_number (1..3, вычисляем по count+1)
	•	attempted_at
	•	attempted_by_user_id
	•	channel enum: call | sms | email | whatsapp | messenger
	•	result enum: no_answer | answered | wrong_number | unavailable
	•	note (опционально)

Ограничения:
	•	нельзя создать attempt_number > 3.
	•	нельзя редактировать попытку; только добавлять новую.

⸻

5.2 UI

Кнопка: Zarejestruj próbę kontaktu
	•	при нажатии — открывается модалка:
	•	канал
	•	результат
	•	заметка
	•	система проставляет attempt_number автоматически.

Показ в карточке:
	•	список попыток с датами, каналом и результатом.

⸻

5.3 Автоматическое завершение после 3 неудач

Правило:
	•	если создана 3-я попытка с result=no_answer (или все три не answered):
	•	появляется CTA: Zakończ – brak kontaktu
	•	система отправляет финальное сообщение и переводит кандидата в отклонённые.

Финальное сообщение

Канал по умолчанию:
	•	email, если есть
	•	иначе sms/whatsapp (если есть телефон и интеграция)

Сущность: final_no_contact_notifications
	•	candidate_id
	•	sent_at
	•	channel
	•	template_id
	•	status

Отказ
	•	candidate.status = rejected
	•	rejection_reason_code = no_contact_after_3_attempts
	•	rejection_reason_text (константа + опц. заметка)

⸻

6. Нормализация стран и городов (латиница)

6.1 Справочник стран

Таблица countries
	•	iso2 (PK)
	•	name_pl
	•	name_en (опц.)
	•	aliases (опц. массив)

В candidate хранить:
	•	country_code (iso2) — источник истины
	•	отображение берём из справочника (PL).

⸻

6.2 Города

Требование 1.0 (без внешних API):
	•	поле ввода города принимает любой текст,
	•	система:
	•	сохраняет city_original как введено,
	•	вычисляет city_latin:
	•	если содержит кириллицу → транслитерировать,
	•	если латиница → оставить как есть.
	•	UI для клиента показывает city_latin.

Поля:
	•	city_original
	•	city_latin

То же для:
	•	first_name_original / first_name_latin (если нужно)
	•	last_name_original / last_name_latin
	•	address_original / address_latin

Рекомендация: применить минимум к полям, которые реально болят клиенту:
	•	имя/фамилия
	•	город
	•	адрес (если есть)

⸻

6.3 Валидация/подсказки
	•	если пользователь вводит кириллицу в “клиентские поля” → предупреждение: “Zostanie zapisane alfabetem łacińskim”
	•	но не блокировать (транслит всё равно сработает).

⸻

7. Аудит-лог (обязательно для всего выше)

7.1 audit_events

Единый журнал:
	•	id
	•	tenant_id
	•	entity_type (candidate, handoff, rodo_notification, contact_attempt)
	•	entity_id
	•	event_type (handoff_requested, handoff_accepted, rodo_sent, contact_attempt_logged, rejected_no_contact, etc.)
	•	actor_user_id
	•	created_at
	•	payload jsonb (доп. данные)

События, которые обязаны логироваться:
	•	RODO отправлено/не отправлено (ошибка)
	•	попытка контакта
	•	handoff requested/accepted/rejected/returned
	•	смена processor (если будет)
	•	финальный отказ “не отвечает”

⸻

8. Уведомления

8.1 События и получатели
	1.	handoff_requested

	•	получатели: назначенный processor или все с ролью client_processor
	•	канал: in-app + (опц.) email

	2.	handoff_accepted / handoff_rejected

	•	получатели: агентский manager + инициатор передачи
	•	включить причину отказа

	3.	handoff_returned

	•	получатели: агентский manager

	4.	rodo_sent_failed

	•	получатели: агентский manager (чтобы вручную связаться)

⸻

9. Шаблоны сообщений

9.1 RODO email template (PL)

Хранить как шаблон в tenant agency:
	•	subject
	•	body
	•	переменные: имя, ссылка на klauzula, компания агентства

9.2 Final no-contact template (PL)

Короткое уведомление о закрытии процесса из-за отсутствия контакта.

⸻

10. Acceptance Criteria (что считается “готово”)
	1.	RODO анкета:

	•	без checkbox нельзя отправить
	•	согласие логируется с версией документа

	2.	RODO FB-лид:

	•	кнопка “Wyślij informację RODO” отправляет email и создаёт immutable запись
	•	дата отправки не может быть изменена
	•	повторная отправка создаёт отдельную запись, не перезаписывает первую

	3.	Контактные попытки:

	•	можно создать максимум 3
	•	попытки immutable
	•	после 3 неудач система предлагает “Zakończ – brak kontaktu” и фиксирует отказ + отправку финального сообщения

	4.	Handoff:

	•	агентство может передать кандидата
	•	клиент видит в inbox и может принять/отклонить с причиной
	•	до accepted клиент не может редактировать
	•	после accepted агентство не может редактировать
	•	возврат возвращает права агентству

	5.	Processor:

	•	после accepted назначается processor
	•	отображается в карточке
	•	фильтр у клиента “Do procesowania” работает

	6.	Страны/города:

	•	страна хранится как ISO код
	•	город/адрес показываются клиенту латиницей (translit)
	•	оригинал сохраняется

	7.	Audit:

	•	все ключевые действия фиксируются в audit_events

⸻

11. Порядок внедрения (техническая очередность)
	1.	Audit events (скелет)
	2.	Legal documents + RODO email лог (без UI — можно API)
	3.	Contact attempts + auto “no contact”
	4.	Handoff + ACL переключение edit/read-only
	5.	Processor / participants
	6.	Notifications
	7.	Country/city normalization (миграции + UI)
	8.	Полировка UI и массовые операции

⸻

12. Важные запреты (чтобы не убить систему)
	•	Никаких “галочек с датой”, которые можно снять и поставить заново.
	•	Все даты — только через события.
	•	Этапы не используются для границ ответственности.
	•	Общий аккаунт клиента запрещён (только персональные учётки).
