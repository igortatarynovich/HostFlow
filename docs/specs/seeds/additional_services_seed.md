# Additional Services Seeds

Дата актуализации: март 2025

Используется в `backend/app/db/seeds/dev_full_seed.py` для локальной разработки.

## Каталог услуг

Создаётся 10 типовых записей:

| Код | Название | Категория | Базовая цена | Требует расписания | Требует кандидата | Документ |
|-----|----------|-----------|--------------|---------------------|-------------------|----------|
| medical | Медосмотр | medical | 350 PLN | Да | Да | medical |
| psychotest | Психотест | medical | 180 PLN | Да | Да | psychotest |
| code95_training | Курс Code 95 | training | 950 PLN | Да | Да | qualification_code95 |
| adr_training | ADR тренинг | training | 1250 PLN | Да | Да | adr_certificate |
| visa_support | Поддержка по визе | legal | 650 PLN | Нет | Нет | visa_or_title |
| attestation_support | ŚK | legal | 420 PLN | Нет | Да | attestation |
| work_permit_support | Разрешение на работу | legal | 550 PLN | Нет | Да | work_permit |
| translation | Нотариальные переводы | legal | 90 PLN | Нет | Нет | — |
| airport_transfer | Трансфер | logistics | 250 PLN | Да | Да | — |
| accommodation | Проживание | logistics | 780 PLN | Да | Да | — |

## Образцы заказов

1. Кандидат `medical + psychotest` — статус `scheduled`, есть расписание для обеих услуг.
2. Кандидат `qualification_code95 + adr_training` — статус `in_progress`, ADR помечен как блокирующий.
3. Компания пакет `visa_support` на группу водителей — статус `quoted`.

Для заказов добавляются расписания, вложения и аудит, что позволяет фронтенду отображать реальные сценарии.
