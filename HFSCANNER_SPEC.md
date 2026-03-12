# HFScanner v1.1 — ТЗ и план по спринтам

## 0. Цель
- Рабочий сканер документов (камера/файл, рамка, детект, ручная правка, warp, фильтры, PDF).
- Готовить датасет для будущей ML-модели детектора.

## 1. Спринт 1 — Бэкенд scanner-api
- Эндпоинты: GET `/scan/health`, POST `/scan/process-page`, POST `/scan/build-pdf` (batch опционально).
- Вход `/scan/process-page` (FormData): `original` (обяз.), `cropped` (опц.), `frame_rect`, `original_size`, `cropped_size`, `manual_contour` (4–8 точек в координатах cropped), `document_kind`, `document_type_id`, `page_code`, `page_index` (обяз.), `expected_pages` (обяз.), `template_aspect_ratio`, `filter`, `detect_only`.
- Порядок:
  1) Read FormData/JSON, sizes.
  2) Базовое изображение для детекта: `cropped` если есть; иначе `frame_rect` crop; иначе full `original` (логируем отсутствие рамки).
  3) Даунскейл для детекта: MAX_DETECT_SIDE=1600.
  4) detect_only=true: запустить детектор; успех 200 `{status:"ok", contour:[6 pts], image_size:{w,h}}`; нет контура → 422 `{status:"NO_CONTOUR_IN_FRAME"}`; файлы не сохранять.
  5) detect_only=false: если `manual_contour` → warp сразу; иначе детектор. Если контур найден → warp. Если нет: при наличии `frame_rect` → 422 `NO_CONTOUR_IN_FRAME` (можно вернуть debug crop URL); без frame_rect → 422 `NO_CONTOUR`.
  6) Warp (см. ниже), фильтр, сохранить `<page>_raw.png`, `<page>_processed.png` в `SCAN_STORAGE_ROOT/<session>/`.
  7) Обновить `session_meta.json` (kind/type/expected_pages/pages).
  8) Ответ: `{processed_url, page_index, width, height}`.
- Детектор:
  - Препроцесс: grayscale → CLAHE → blur(5x5) → edges/threshold (Canny+threshold).
  - ROI: работать по cropped/ROI; площади 12–92% ROI, extent ≥0.55.
  - approxPolyDP до 4–8 вершин; кандидаты только четырёхугольники.
  - Аспект: шаблон ±12%.
  - Скоринг: `score = 0.6*area_norm + 0.4*aspect_score`, aspect_score = 1 - min(|ARfact-ARtempl|/(0.12*ARtempl),1).
  - Возврат 4 углов в стабильном порядке.
- Warp + trim:
  - 4 угла → `warpPerspective` на длинную сторону 2000 px, короткая = round(2000 / template_ar).
  - Обрезка пустых полей по маске “нечёрных”, расширить на 2–3 px; если AR сильно уехал (>15%) — лог warn.
  - Сохранить warped_raw.
- Фильтры:
  - standard: grayscale → CLAHE → лёгкий sharpen.
  - document/bw: grayscale → adaptiveThreshold (подобрать).
  - photo: мягкий контраст/яркость без потери деталей.
- `/scan/build-pdf`:
  - Валидация expected_pages; 422 MISSING_EXPECTED_PAGES/MISSING_PAGES/EXTRA_PAGES.
  - Собрать `document_<kind>_<ts>.pdf` из *_processed по порядку 0..N-1.

## 2. Спринт 2 — Фронт HFScanner v1
- Стейты: SCAN → EDIT → PROCESSING → REVIEW → DONE_PAGE → DONE_DOCUMENT (строгие переходы).
- SCAN: камера/файл, фиксированная рамка (по аспекту шаблона, ~80–85% ширины, затемнение вокруг). Снимок возможен вручную. После снимка фронт обрезает по рамке (`cropped`), сохраняет `frame_rect`, отправляет detect_only для автоконтурa (не блокируя UI).
- EDIT: превью `cropped` с контуром (4 угла + midpoints), ограничения по отступам/минимальному размеру. “Применить” → PROCESSING (POST `/scan/process-page` с `manual_contour`, original/cropped/sizes/frame_rect/…).
- PROCESSING: оверлей; успех → REVIEW; ошибки (NO_CONTOUR_IN_FRAME) → сообщение и назад в EDIT/SCAN.
- REVIEW: показываем processed_url; кнопки “Переснять”, “Исправить границы”, “Подтвердить страницу” → DONE_PAGE.
- DONE_PAGE: если есть следующая страница → page_index++ → SCAN; если последняя → `/scan/build-pdf` → DONE_DOCUMENT.
- DONE_DOCUMENT: показать PDF + “Скачать” и “Отправить в анкету” (uploadPublicScanPdf/attach).
- Контур на фронте: 4 угла + midpoints (30% сегментов, isCustom), углы двигают соседние midpoints если не кастом; midpoints при drag → isCustom=true, clamp, не ближе 10–15 px к углам. Отправка на бэк — минимум 4 угла (midpoints опционально для логов).
- Вызовы `/scan/process-page`: всегда оригинал+cropped+sizes+frame_rect+manual_contour+page_index/expected_pages/doc kind, без detect_only в основном потоке.
- Доп. UX для редактирования контура:
  - ✔ haptic feedback при захвате/перетаскивании точки (iOS/Android).
  - ✔ auto-drag smoothing (как в Instagram story editor) — сглаживание движения точки.
  - ✔ градиентный контур для лучшей видимости на светлом/тёмном фоне.

## 3. Спринт 3 — Интеграция (public анкета + тест)
- /public: форма -> создаёт public intake + токен -> редирект /public/apply/:token.
- /public/apply/:token: анкета; в блоке документов кнопка “Сканировать” → создаёт/получает scan_session → открывает /public/scan?session_id&document_type&expected_pages&return_to.
- /public/scan: HFScanner в public-режиме, по завершении PDF уходит в intake.
- /public/hfscanner-test: без токена, выбор типа документа (ID/DRIVER_LICENSE/TACHO_CARD/CODE95_CARD/PASSPORT_SPREAD/A4), тот же HFScanner; в DONE_DOCUMENT — ссылка на PDF + короткая анкета (оценка рамки 1–5, комментарий) для логов.

## 4. Спринт 4 — Логирование для ML
- При подтверждённой странице (после REVIEW -> DONE_PAGE): писать JSONL/БД с:
  - session_id, document_kind, document_type_id, page_index, expected_pages, timestamp.
  - Пути: original, cropped, raw, processed.
  - Геометрия: original_size, cropped_size, frame_rect.
  - auto_contour (если был детект), manual_contour_front (все точки с фронта), final_contour_used.
  - filter, source (public_apply | hfscanner_test), rating/comment (для тест-страницы).
- Цель — собрать датасет “изображение → правильный контур, тип документа”.

## DoD
- Спринт 1: пайплайн бэка по 1.3–1.6, детектор 1.4, warp/trim 1.5, фильтры 1.6, ошибки согласованы; build-pdf валидирует страницы.
- Спринт 2: фронт-стейт-машина и UX из раздела 2.
- Спринт 3: public/apply/scan работает, pdf уходит в анкету; доступен hfscanner-test.
- Спринт 4: логи с полной геометрией/путями/типами + оценки с тест-страницы.
