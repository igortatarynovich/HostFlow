# ADR-008: Job Publishing / Job Distribution (внутри Recruitment)

## Status

**Accepted (product & architecture direction).** Имплементация **поэтапная**. Текущий код (вакансии, публичные страницы, лиды) может **частично** совмещать «вакансию» и «публикацию» — целевая модель ниже задаёт **разделение сущностей** для эволюции без превращения вакансии в кандидата или смешения с Finance/Services.

## Context

Нужен явный слой **публикации и распространения вакансий**: внутренняя потребность (vacancy) ≠ публичное объявление (job post) ≠ канал размещения (publishing channel). Отклики должны входить через **Forms** ([`ADR-007`](ADR-007-forms-platform-capability.md)) и порождать **Lead/Candidate**, с трассировкой **source / channel / campaign**.

**Job Publishing** — **не** отдельный основной бизнес-модуль уровня HR / Fleet / Finance (ADR-004). Это **capability внутри Recruitment** или **addon к Recruitment** + опционально **marketplace-интеграции** для конкретных job-порталов ([`ADR-006`](ADR-006-marketplace-and-integration-platform.md)).

Зависимость:

- Если у компании / workspace **нет модуля Recruitment** (`recruitment` выключен) — **Job Publishing недоступен**.  
- Если Recruitment **включён**, Job Publishing может быть: **включён базово** (basic), **расширен платным addon** (advanced), плюс **платные/бесплатные коннекторы** порталов через Marketplace.

Связанные ADR:

- [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) — Recruitment как продуктовый модуль.  
- [`ADR-007`](ADR-007-forms-platform-capability.md) — форма отклика = input layer.  
- [`ADR-005`](ADR-005-three-level-settings-hierarchy.md) — настройки recruitment per company.  
- [`ADR-006`](ADR-006-marketplace-and-integration-platform.md) — интеграции порталов как extensions.

---

## Decision: сущности и границы

### 1. Vacancy (внутренняя потребность)

Внутренняя сущность компании: **кого ищем**, для какой **company**, условия, требования, **headcount**, **`owner_company_id`**, **status** жизненного цикла вакансии.

- **Не** путать с **Candidate** и **pipeline кандидата**: вакансия — **спрос**, кандидат — **предложение** в подборе.  
- Вакансия **не** является «кандидатом» и **не** живёт в воронке кандидата как substitute.

### 2. Job Post (внешняя публикация)

Публичная **версия** вакансии для вывода наружу:

- Заголовок, описание, **язык**, отображение зарплаты, локация  
- Ссылка на **application form** (контур Forms)  
- **Publication status** (черновик, активна, приостановлена, закрыта и т.п. — уточнение продуктом)

**Связь:** одна **Vacancy** → **много Job Posts** (языковые варианты PL/RU/UA/EN, разные порталы, разные версии кампании, A/B).

### 3. Publishing Channel

**Куда** публикуем (логический тип + при необходимости инстанс интеграции):

- OLX, Pracuj.pl, Indeed, Facebook/Meta, LinkedIn  
- **Company career page**  
- **Public HostFlow job page**  
- Другие — через каталог каналов и Marketplace-коннекторы

Канал связывает **Job Post** с внешней площадкой и метаданными размещения (внешний id, ссылка, статус синхронизации).

### 4. Application Form

Форма отклика, созданная в модуле **Forms** ([`ADR-007`](ADR-007-forms-platform-capability.md)):

- Intake кандидата, загрузка документов, RODO consent, предквалификация  

**Правило:** публичная публикация вакансии **использует форму как точку входа** кандидата; Forms — **input layer**, не дублируем «анкету только в Recruitment» в обход Forms.

---

## Целевой flow

```
Vacancy → Job Post → Publishing Channel → Application Form → Lead / Candidate
```

- **Candidate** создаётся из **submitted application** (и/или Lead — по правилам tenant).  
- Сохранять **source / channel / campaign** (и при необходимости UTM) для аналитики и атрибуции.  
- **Закрытие публикации** не обязано удалять Vacancy — только останавливает внешний приём откликов по соответствующим Job Post / каналам.

---

## Состав Recruitment module (целевой перечень)

Recruitment **должен** покрывать (включая текущий и плановый функционал):

- **Vacancies**  
- **Vacancy templates**  
- **Job posts**  
- **Application forms** (через Forms; привязка к post)  
- **Publication channels**  
- **Job portal integrations** (базовые + marketplace)  
- **Application tracking** (отклики, статусы, конверсии)

---

## Монетизация и слои

| Уровень | Описание |
|---------|----------|
| **Basic** | Часть Recruitment: создать вакансию, job post(ы), публикация на ограниченном наборе каналов (например career page / HostFlow job page), форма отклика, создание lead/candidate |
| **Advanced addon** | Мультипосты, много каналов, кампании, расширенная аналитика конверсии channel → candidate, SLA по откликам — по политике продукта |
| **Marketplace** | Коннекторы к отдельным job boards (Indeed, Pracuj, …) как integrations/apps ([`ADR-006`](ADR-006-marketplace-and-integration-platform.md)) |

---

## Архитектурные запреты

1. **Не смешивать** сущность **Vacancy** и **candidate pipeline** как одну модель.  
2. **Не** размещать доменную логику **Job Publishing** в **Finance** или **Services** (рекрутинговая публикация — контур Recruitment).  
3. **Application Form** не подменяет **Job Post**; пост описывает **оффер наружу**, форма — **ввод данных** отклика.

---

## Возможности (backlog продукта)

- Создание вакансии и **нескольких** job posts  
- Публикация на **разных каналах**  
- Приём откликов через Forms  
- Автоматическое создание **leads/candidates**  
- Видимость **source / channel / campaign**  
- Закрытие публикации без путаницы со статусом вакансии  
- Метрики **конверсии channel → candidate**

---

## Consequences

1. Новые фичи «вакансия наружу» моделируются как **Job Post + Channel + Form**, а не как расширение только `Vacancy` без поста.  
2. Команда Forms и Recruitment согласуют **контракт привязки** формы к job post / vacancy.  
3. Документ [`../../recruitment/module-scope.md`](../../recruitment/module-scope.md) и каталог маршрутов отражают этот слой.

## References

- [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md)  
- [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md)  
- [`ADR-005`](ADR-005-three-level-settings-hierarchy.md)  
- [`ADR-006`](ADR-006-marketplace-and-integration-platform.md)  
- [`ADR-007`](ADR-007-forms-platform-capability.md)  
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)  
- [`../../recruitment/module-scope.md`](../../recruitment/module-scope.md)

## История

- 2026-05: первичная фиксация Vacancy / Job Post / Publishing Channel / Application Form, flow, зависимость от Recruitment и Forms, basic/advanced/marketplace.

