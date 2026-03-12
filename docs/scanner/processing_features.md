# Функции обработки документов (сканер)

## Результаты тестирования

- **Обработка:** детекция, перспектива, кроп, deskew, ресайз до A4 — работают
- **Фильтры:** `standard`, `strong` (бинар.), `photo` — работают
- **Manual contour:** 6 точек, piecewise affine — работает
- **Frontend → Backend:** `meta.enhancement_mode`, `meta.manual_contour` — передаются корректно

## Интеграция

- API: `/public/scan-sessions/{session_id}/pages`
- Frontend: `meta.enhancement_mode` (`standard`|`strong`|`photo`), `meta.manual_contour` (6 точек)
- Backend: `ImagePreprocessor.process()` с `enhancement_mode` и `manual_contour`
