# Тестирование Document Scanner

## 🚀 Быстрый старт

### Вариант 1: Автоматический тест (рекомендуется)

```bash
# 1. Посмотреть все доступные пресеты
docker compose exec backend python backend/scripts/test_scanner.py \
  --tenant-id 11111111-1111-1111-1111-111111111111 \
  --list-presets

# 2. Запустить полный тест (создаст сессию, загрузит тестовое изображение, обработает)
docker compose exec backend python backend/scripts/test_scanner.py \
  --tenant-id 11111111-1111-1111-1111-111111111111 \
  --doc-type driver_license

# 3. Получить Web URL для тестирования в браузере
docker compose exec backend python backend/scripts/test_scanner.py \
  --tenant-id 11111111-1111-1111-1111-111111111111 \
  --doc-type driver_license \
  --web-url
```

Скрипт автоматически:
- ✅ Создаст публичную заявку (получит token)
- ✅ Создаст сессию сканирования
- ✅ Загрузит тестовые изображения
- ✅ Обработает сессию
- ✅ Покажет результаты с оценкой качества

### Вариант 2: Через Web UI (публичная страница)

1. Получите token через скрипт (см. выше) или API
2. Откройте в браузере:
```
https://hostflow.cc/public/scan?token=<TOKEN>&doc=<DOC_TYPE>
```

**Параметры:**
- `token` - Magic link token от кандидата
- `doc` - Тип документа (например: `driver_license`, `passport`, `id_card`)

**Примеры:**
```
https://hostflow.cc/public/scan?token=abc123&doc=driver_license
https://hostflow.cc/public/scan?token=abc123&doc=passport
https://hostflow.cc/public/scan?token=abc123&doc=id_card
```

### Вариант 3: Через API (для тестирования)

#### Шаг 1: Получить magic link token

```bash
# Создать публичную заявку (получить token)
curl -X POST https://hostflow.cc/api/v1/public/intake \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: <TENANT_ID>" \
  -d '{
    "contacts": {
      "phone_country_code": "+48",
      "phone": "555123456"
    }
  }'
```

Ответ содержит `token` - используйте его для сканирования.

#### Шаг 2: Создать сессию сканирования

```bash
curl -X POST https://hostflow.cc/api/v1/public/scan-sessions \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: <TENANT_ID>" \
  -d '{
    "token": "<TOKEN_FROM_STEP_1>",
    "document_type": "driver_license"
  }'
```

Ответ содержит `id` сессии.

#### Шаг 3: Загрузить страницу документа

```bash
curl -X POST https://hostflow.cc/api/v1/public/scan-sessions/<SESSION_ID>/pages \
  -H "X-Tenant-Id: <TENANT_ID>" \
  -F "file=@/path/to/image.jpg" \
  -F "page_code=front" \
  -F "rotation=0"
```

#### Шаг 4: Обработать сессию

```bash
curl -X POST https://hostflow.cc/api/v1/public/scan-sessions/<SESSION_ID>/process \
  -H "X-Tenant-Id: <TENANT_ID>"
```

#### Шаг 5: Получить результат

```bash
curl https://hostflow.cc/api/v1/public/scan-sessions/<SESSION_ID> \
  -H "X-Tenant-Id: <TENANT_ID>"
```

## 📋 Доступные типы документов

### Карты (ID-1 формат, 85.6x54mm)
- `id_card` - ID карта
- `national_id` - Национальный ID
- `residence_permit` / `residence_card` - Карта pobytu
- `driver_license` - Водительские права
- `tachograph_card` - Карта тахографа
- `visa` - Виза

### Паспорта
- `passport` - Паспорт (разворот с фото)
- `passport_main` - Паспорт (разворот)
- `passport_all` - Паспорт (все страницы)

### Сертификаты (A5/A4)
- `qualification_code95` / `code95` - Code 95
- `adr_certificate` / `adr` - Сертификат ADR
- `medical_certificate` - Медицинская справка
- `criminal_record` - Справка о несудимости
- `psychology_test` / `psych_tests` - Психологические тесты
- `work_permit` - Разрешение на работу

### A4 документы
- `contract` / `employment_contract` - Контракт
- `insurance` - Страховка
- `bhp` - BHP обучение
- `assignment` - Назначение
- `accommodation` - Жильё
- `bank_account_confirmation` - Банковская выписка

### Фото
- `photo` / `photo_35x45` - Фото 35x45mm

## 🧪 Тестирование функций

### Автоматический захват
1. Откройте страницу сканирования на мобильном устройстве
2. Наведите камеру на документ
3. Система автоматически проанализирует качество
4. Когда качество хорошее и стабильное (5+ кадров) - произойдёт автоматический захват

### Фильтры изображений
При загрузке страницы можно указать `filter_name`:
- `grayscale` - Чёрно-белое
- `binarization` - Бинаризация OTSU
- `binarization_adaptive` - Адаптивная бинаризация
- `binarization_color` - Цветная бинаризация
- `antialiasing` - Сглаживание краёв
- `magic_color` - Улучшение цветов

### Экспорт в разных форматах
После обработки доступны:
- JPG: `{page_code}-processed.jpg`
- PNG: `{page_code}-processed.png`
- TIFF: `{page_code}-processed.tiff`

## ✅ Проверка качества

После обработки проверьте:
- `quality_score` - числовая оценка (0.0 - 1.0)
- `quality_level` - уровень: `very_poor`, `poor`, `fair`, `good`, `excellent`
- `issues` - список проблем (если есть)

## 🔧 Тестирование через pytest

```bash
docker compose exec backend pytest backend/tests/api/test_public_intake.py::test_public_scanner_flow -v
```
