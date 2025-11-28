# HostFlow i18n — Candidate Intake & Docs (Step 1)

## 1. Область и подход
- Покрыты **все пользовательские поверхности**, затронутые задачей: публичный портал кандидата (landing, intake start, анкета, статус), модуль документов в админке и ключевые рабочие экраны (доски, пайплайн, профили, сервисы, навигация).
- Для поиска строк использовались `rg -n "[А-Яа-я]"` и точечные просмотры файлов; в таблицах ниже приведены ссылки `path:line`, сгруппированные по функциональным блокам.
- Перечислены как русские, так и английские literal-строки — обе категории нужно вынести в `en/ru/pl`.

## 2. Инвентаризация строк

### 2.1 Публичный портал кандидата
| Экран / файл | Копирайт и блоки | Предлагаемый префикс |
| --- | --- | --- |
| `src/pages/public/PublicApplyPage.tsx`<br/>`23-213`, `239-287`, `371-1082`, `673`, `720-874` | Stepper/чек-лист: `'Обзор', 'Контакты', … 'Согласия'`; подсказки готовности профиля/доков; статусы `'Анкета отправлена'`, `'Черновик'`; уведомления и тосты (`'Ссылка отправлена…'`, `'Не удалось загрузить документ'`, `'Новая ссылка создана'`); карточки статов `'Статус заявки'`, `'Документы'`, `'Профиль'`; документы/формы (`'Типы прицепов'`, `'Маршруты'`, `'Добавить опыт'`, `'Прицепы'`, `'Маршруты'`, `'Добавить/Сохранить'`, `'Не выбрано'`, `'EU / EEA / CH'`, `'Виза'`, `'ВНЖ / карта побиту'`); CTA `'Отправить анкету'`, `'Черновик сохраняется автоматически'`. | `public.intake.*` (`steps.*`, `checklist.*`, `notifications.*`, `documents.*`, `forms.*`, `cta.*`) |
| `src/pages/public/PublicPortalLanding.tsx`<br/>`54-247` | Хиро и подзаголовки `'Портал кандидата…'`, `'Presign загрузка…'` (EN); карточки для нового кандидата, продолжения, восстановления ссылки; тексты ошибок `'Ссылка недействительна…'`, `'Введите код доступа…'`, `'Укажите email…'`; плейсхолдеры `например, aBcdEf123…`. | `public.portal.hero.*`, `public.portal.cards.*`, `public.portal.magic_link.*` |
| `src/pages/public/PublicIntakeStart.tsx:32-139` | Условия старта `'Укажите телефон или email…'`, состояния загрузки `'Создаём ссылку…'`, ошибки `'Не удалось создать анкету'`. | `public.start.*` |
| `src/pages/public/PublicStatusPage.tsx:32-205` | Заголовки `'Статус заявки кандидата'`, описание токена, статусы `'Текущий статус'`, предупреждения `'Ссылка временная'`, карточка документов (`'Обязательные', 'Готово', 'Ожидает', 'Отсутствует'`, `'Обязательный документ' / `'Опционально / по запросу'`, `'Открыть файл'`), пустое состояние `'Ссылка недействительна или истекла'`. | `public.status.*` (`hero`, `badges`, `timeline`, `documents`, `errors`) |
| `src/pages/public/components/PublicTimeline.tsx:9-74` | Плейсхолдер `'Статусы появятся…'`, fallback `'Анкета создана', 'Черновик сохранён', 'Данные заполнены', 'Документы загружены', 'Анкета отправлена'`, статус `'Готово X/Y'`. | `public.timeline.*` |
| `src/modules/public-intake/usePublicIntake.ts:53-116` | Ошибки `'Не удалось загрузить анкету'`, `'Не удалось сохранить изменения'`, `'Не удалось отправить анкету'`. | `public.api.intake.*` |
| `src/modules/public-intake/usePublicStatus.ts` | Сообщения `'Не удалось загрузить статус'`, `'Ссылка недействительна'`. | `public.api.status.*` |

### 2.2 Модуль документов в админке
| Файл | Копирайт и блоки | Префикс |
| --- | --- | --- |
| `src/modules/documents/CandidateDocuments.tsx`<br/>`56-200`, `339-953`, `1300-1700` | Справочники статусов/процессов/источников (`'Отсутствует', 'Запрошен', …`, `'Водительские', `'Разрешение на работу'`, `'Кандидат/Работодатель/Агентство'`); требования сканера (`'Общий размер ≤ … МБ'`, `'Сканирование двух сторон'`, `'Соблюдайте порядок съёмки'`); алерты/твисты (`'Файл слишком большой'`, `'Укажите дату заказа'`, `'Документ заказан/загружен/создан'`); ошибки прав `'У вас нет прав…'`; CRUD сообщения `'Документ удалён', 'Статус обновлён', 'Документ отклонён'`; workflow UI (`'Процесс', `'Заказать'`, `'заказан'` и т.п.). | `admin.documents.*` (поддеревья `status`, `process`, `requirements`, `notifications`, `errors`, `workflow`, `actions`) |
| `src/pages/DocumentsRegistryPage.tsx:8-26` | Плейсхолдер `'Глобальный реестр документов…'`, подписи `'Поиск по документам'`, `'ID кандидата…'`, `'Следующий релиз…'`. | `admin.documents.registry.*` |
| `src/pages/admin/DocumentTypesPage.tsx:9-44` | HUD `'Каталог типов документов'`, `'Здесь появится…'`, заголовки таблицы `'Код', 'Название', 'Обязательная загрузка'`, бейджи `'Да', 'Опционально'`. | `admin.documents.types.*` |

### 2.3 Навигация и ключевые рабочие экраны
| Область | Файлы / строки | Ключевые строки | Префикс |
| --- | --- | --- | --- |
| Навигация/хром | `src/components/Layout.tsx:55-232`, `src/components/nav/Topbar.tsx:93-325`, `src/components/nav/Sidebar.tsx:97` | Названия разделов (`'Дашборд', 'Компании', … 'Выйти'`), подсказки `'Переключить меню'`, `'Поиск кандидатов, компаний, документов…'`, `'Напоминания'`, `'Профиль'`, `'Открыть меню'`, `'Закрыть меню'`. | `nav.*` (`nav.sidebar.*`, `nav.topbar.*`, `nav.actions.*`) |
| Аутентификация | `src/pages/Login.tsx:22-50` | `'Вход в HostFlow'`, ошибки `'Неверный email или пароль…'`, `'Ошибка входа. Попробуйте позже.'`, кнопки `'Входим…' / 'Войти'`. | `auth.login.*` |
| Дашборд | `src/pages/Dashboard.tsx:56-449` | Быстрые диапазоны `'7 дней'…`, измерения `'Статус/Компания…'`, ошибки `'Дата начала больше даты окончания'`, `'Ошибка загрузки данных'`, кнопки `'Обновление…/Обновить'`, подписи `'дате создания/обновления'`. | `dashboard.*` |
| Кандидаты (список + карточка) | `src/pages/Candidates.tsx:29-1636`, `src/pages/CandidateCard.tsx:182-2279`, `src/components/StageTag.tsx:26-49`, `src/pages/Pipeline.tsx:541-964` | Метки статусов `'Не начато', 'Заказан', …`, массовые действия (`'Массово назначить менеджера'` и т.д.), подписи таблиц (`'Имя', 'Телефон', 'Статус документов'`), тосты (`'Не удалось загрузить список кандидатов'`), карточка `'Личные данные', 'Опыт', 'Документы', 'Запросить удаление'`, пайплайн ошибки `'Не удалось загрузить пайплайн'`. | `candidates.list.*`, `candidates.card.*`, `pipeline.*` |
| Компании | `src/pages/Companies.tsx:56-2586` | Сотни лейблов разделов (`'Готовность профиля', 'Юридический блок', 'Биллинг и счета', …`), статусы `'Да/Нет', 'Из архива/В архив'`, сообщения `'Не удалось сохранить изменения'`. | `companies.*` (подмодули `status`, `sections`, `form_labels`, `errors`) |
| Профиль пользователя | `src/pages/ProfilePage.tsx:26-759` | Настройки уведомлений `'Новый кандидат…'`, варианты `'Сразу', 'Дайджест раз в день'`, вкладки `'Кандидаты/Вакансии'`, сообщения `'Профиль обновлён'`, `'Пароль обновлён'`, формы (`'Имя', 'Фамилия', 'Тема'…), CTA `'Сохранение…/Сохранить'`. | `profile.*` |
| Сервисы / услуги | `src/pages/ServicesPage.tsx:140-970` | Ошибки (`'Услуга успешно добавлена'`, `'Не удалось создать заказ'`, `'Расписание обновлено'`), статусы `'Активна/Архив'`, формы (`'Поиск кандидата…'`, `'Код услуги'`, `'Цена'`, `'Заметки'`), пустые значения `'Без владельца'`. | `services.*` |
| Напоминания | `src/pages/RemindersPage.tsx:11-93` | Категории событий `'Новый кандидат из лида'`, фильтры `'для вас' / 'все события'`, ошибки загрузки/очистки. | `reminders.*` |
| Лиды | `src/pages/LeadsPage.tsx:8-53` | Фильтры `'Все статусы', 'Новый', …`, ошибка `'Не удалось загрузить лиды'`. | `leads.*` |
| Документы / контрольные элементы | `src/components/controls/*.tsx` | Плейсхолдеры `'Поиск страны/кода…'`, `'номер'`, `'Выберите значения'`, `'— выбрать —'`, `'Выберите…'`. | `controls.*` |
| Вакансии | `src/components/vacancies/VacancyForm.tsx`, `VacancyList.tsx`, `VacancyDetail.tsx` | Ошибки `'Компания обязательна'`, фильтры `'Все/Открыта/…'`, столбцы `'Название/Компания/Статус'`, действия `'Обновление…'`, предупреждения `'Удалить вакансию?…'`. | `vacancies.*` |
| Админ-настройки | `src/pages/admin/UsersPage.tsx`, `SettingsLandingPage.tsx`, `RulesetVersionsPage.tsx`, `DeletionRequestsPage.tsx`, `CompanyAccessPage.tsx`, `MetaLeadsAdminPage.tsx` | Карточки `'Пользователи и роли'`, статусы `'Активен/Приглашён'`, действия `'Обновить', 'Одобрить', 'Выдать доступ'`, многочисленные ошибки `'Не удалось загрузить …'`. | `admin.settings.*`, `admin.users.*`, `admin.ruleset.*`, `admin.deletion.*`, `admin.company_access.*`, `admin.meta_leads.*` |

> **Наблюдение:** многие значения (статусы документов, типов процессов, пайплайн-этапы) уже приходят с backend. Для i18n стоит либо получать локализованные лейблы из API, либо завести единые ключи, чтобы не дублировать словари по фронту/беку.

## 3. Предлагаемая структура ключей и ресурсов

```
src/i18n/
  en.json   # source язык
  ru.json   # зеркальная структура
  pl.json   # зеркальная структура
```

Рекомендуемое дерево (дополняет требования из `docs/specs/i18n/index.md`):

```
common.loading
common.actions.save / cancel / delete / copy_link
nav.sidebar.dashboard / companies / ...
nav.topbar.search.placeholder / notifications / profile

auth.login.title / submit / errors.invalid_credentials / errors.generic

public.portal.hero.title / bullets.presign / cards.new.* / cards.resume.* / cards.resend.*
public.start.form.instructions / errors.submit_failed
public.intake.steps.overview ... agreements
public.intake.checklist.profile_ready_hint / documents_ready_hint
public.intake.notifications.copy_success / copy_error / magic_link_sent / magic_link_error
public.intake.forms.contacts.phone_placeholder / residency_status.eu / visa / card / none
public.intake.documents.upload_error / upload_cta / stats.title / stats.profile / stats.documents
public.timeline.empty / fallback.intake_created.title / ...
public.status.hero.title / hero.description / badges.current_status / warnings.token_expiry / documents.summary.*
public.api.intake.load_failed / save_failed / submit_failed

documents.scanner.accept_formats / max_total / ...
documents.status.missing / requested / ...
documents.labels.requested_from_driver / ...
documents.meta_fields.number / expires_at / ...

admin.documents.actions.upload / order / approve / reject
admin.documents.errors.no_permissions / upload_failed / delete_failed / status_update_failed
admin.documents.registry.empty_state / search_placeholder
admin.documents.types.table.code / name / required

dashboard.range.7d / 30d / ... ; dashboard.errors.invalid_range
candidates.list.filters.* ; candidates.list.actions.bulk_assign_manager / error.fetch_failed
candidates.card.sections.personal / experience / documents ; candidates.card.actions.request_deletion.*
pipeline.errors.load_failed / update_failed
companies.sections.profile_readiness / legal / billing / ...
profile.notifications.* / forms.labels.* / success.*
services.orders.errors.* / forms.labels.*
reminders.filters.mine / all ; reminders.errors.*
leads.filters.status.* / errors.load_failed
controls.select.placeholder / search
vacancies.filters.status.* / errors.load_failed / actions.export_csv
admin.users.status.active / invited / inactive ; admin.users.actions.invite / revoke_token
admin.settings.cards.users / company_access / documents / ruleset / integrations / audit
admin.ruleset.errors.generic / diff.added / diff.removed
admin.deletion.actions.approve / reject / placeholders.reason_optional
admin.company_access.roles.edit / view / errors.*
admin.meta_leads.forms.connection_name / errors.*
```

### Fallback & загрузка
- Сохраняем существующий `I18nProvider`, но расширяем `RESOURCES` до `{ en, ru, pl }`.
- Source (`en`) — обязательный; `ru` и `pl` должны проходить структурную валидацию (можно переиспользовать `scripts/i18n_sync.py`).
- Фолбэк: `active → en → literal key`. Для ru/pl разрешается временное копирование английского текста, но не пустые строки.
- Параметры форматирования (`{count}`, `{mb}`) стандартизировать: ключ хранит шаблон, компоненты передают `values`.

### Ключевые договорённости
1. **Единый namespace**: `public`, `documents`, `dashboard`, `candidates`, `companies`, `profile`, `services`, `reminders`, `leads`, `controls`, `vacancies`, `admin.*`.
2. **Поля форм**: `*.form.labels.<field>` + `*.form.placeholders.<field>`.
3. **Статусы/списки**: `*.status.<code>` или `*.filters.<code>` — чтобы синхронизировать с backend enums.
4. **Ошибки/тосты**: `*.errors.<scenario>`; успехи — `*.success.<scenario>`.
5. **CTA/кнопки**: `common.actions.*` когда переиспользуемы; иначе `module.actions.*`.

## 4. Следующие шаги
1. Создать `src/i18n/pl.json`, обновить `I18nProvider` (Step 2).
2. Расписать `en.json` по указанной структуре; перенести существующие ключи (`scanner`, `documents`...) в новые места либо оставить алиасы.
3. Пройтись по таблицам выше и заменить литералы на `t('…')`, параллельно наполняя `ru/pl`.
4. Добавить раздел об i18n в `docs/specs/i18n/index.md` (ссылку на этот аудит) после внедрения.
