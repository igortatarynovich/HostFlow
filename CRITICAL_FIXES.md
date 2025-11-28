# КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ

## Проблема: Overlay не отображался

**Причина:** На мобильных устройствах `videoWidth` и `videoHeight` часто равны 0, из-за чего overlay не рендерился.

**Исправление:**
- Добавлен fallback на размеры окна (`window.innerWidth/innerHeight`) когда `videoWidth/videoHeight = 0`
- Overlay теперь всегда виден, даже если видео еще не загрузилось

## Что исправлено:

1. **Overlay всегда виден** - используется fallback на размеры окна
2. **Детекция отображается** - рамка документа теперь видна (желтая/зеленая, толщина 6px)
3. **Все кнопки логируются** - в консоли видны все клики:
   - `[PreviewModal] Filter button clicked` - выбор фильтра
   - `[PreviewModal] Edit contour button clicked` - редактирование границ
   - `[PreviewModal] Send button clicked` - отправка
   - `[PreviewModal] Retake button clicked` - переснять

## Новый bundle:
- `index-CvoeHhnm.js` (1.5 MB) создан в 15:19

## ВАЖНО: Очистите кеш браузера!

1. **Hard Refresh:** `Ctrl + Shift + R` (Windows/Linux) или `Cmd + Shift + R` (Mac)
2. **Или:** DevTools → Application → Clear storage → Clear site data
3. **Проверьте:** В Network tab должен загружаться `index-CvoeHhnm.js`

## Что должно работать после очистки кеша:

✅ **Детекция документа** - рамка видна (желтая/зеленая, 6px)
✅ **Фильтры** - выбор работает, логи в консоли
✅ **Коррекция границ** - редактор открывается
✅ **Отправка** - документ загружается с параметрами
✅ **Переснять** - кнопка работает

## Диагностика:

Откройте DevTools → Console и проверьте:
- `[scanner] Document detected:` - детекция работает
- `[PreviewModal] Filter button clicked` - фильтры работают
- `[PreviewModal] Send button clicked` - отправка работает

Если логи не появляются - проблема в кеше браузера.
