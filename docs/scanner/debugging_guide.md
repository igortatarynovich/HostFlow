# Руководство по отладке сканера документов

## 1. Очистите кеш браузера (КРИТИЧНО!)

Браузер может использовать старый bundle. **Обязательно** сделайте:

- **Hard Refresh:** `Ctrl + Shift + R` (Windows/Linux) или `Cmd + Shift + R` (Mac)
- Или: DevTools → Application → Clear storage → Clear site data
- Или: Правый клик на кнопке обновления → «Очистить кеш и жесткая перезагрузка»

## 2. Проверьте консоль браузера (DevTools → Console)

### Должны быть логи:
- `[scanner] Document detected:` — если документ найден
- `[scanner] PreviewModal: Filter selected` — при выборе фильтра
- `[scanner] PreviewModal: Edit contour button clicked` — при редактировании
- `[scanner] PreviewModal: Send button clicked` — при отправке
- `[scanner] Uploading with meta:` — при загрузке с параметрами

### Не должно быть:
- Ошибок JavaScript (красные сообщения)
- Предупреждений о missing dependencies

## 3. Проверьте Network tab

1. **Запросы к сессии:** не чаще 1 раза в 15 секунд
2. **При отправке:** POST к `/public/scan-sessions/{id}/pages`, в FormData — `meta` с `enhancement_mode` и `manual_contour`
3. **Статус ответов:** все 200 (OK)

## 4. Проверьте backend логи

```bash
cd /opt/HostFlow
docker-compose logs backend --tail 100 -f
```

Ожидаемые логи: `INFO: Processing scan session...`, `INFO: Using enhancement_mode: ...`, `INFO: Using manual contour...` (если указан).

## 5. Ожидаемое поведение после исправлений

1. **Страница НЕ обновляется** — запросы к сессии не чаще 1 раза в 15 секунд
2. **Детекция работает** — документ определяется, появляется рамка
3. **Фильтры работают** — выбор фильтра и отправка с `enhancement_mode`
4. **Коррекция границ** — редактор открывается, точки draggable
5. **Отправка** — документ загружается и обрабатывается с выбранными параметрами
