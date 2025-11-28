# Руководство по отладке сканера документов

## Проблема: "100% проблем остались"

Если все проблемы остались после деплоя, выполните следующие шаги:

---

## 1. Очистите кеш браузера (КРИТИЧНО!)

Браузер может использовать старый bundle. **Обязательно** сделайте:

### Способ 1: Hard Refresh
- **Windows/Linux:** `Ctrl + Shift + R`
- **Mac:** `Cmd + Shift + R`

### Способ 2: Полная очистка
1. Откройте DevTools (F12)
2. Правый клик на кнопке обновления → "Очистить кеш и жесткая перезагрузка"
3. Или: DevTools → Application → Clear storage → Clear site data

### Способ 3: Проверка нового bundle
1. DevTools → Network
2. Перезагрузите страницу (Ctrl+Shift+R)
3. Проверьте что загружается `index-D4BbX2-z.js` (НЕ старый `index-BIGoVSld.js` или `index-BqzT2exW.js`)

---

## 2. Проверьте консоль браузера

Откройте DevTools → Console и проверьте:

### Должны быть логи:
- `[scanner] Document detected:` - если документ найден
- `[scanner] PreviewModal: Filter selected` - при выборе фильтра
- `[scanner] PreviewModal: Edit contour button clicked` - при нажатии на редактирование
- `[scanner] PreviewModal: Send button clicked` - при отправке
- `[scanner] Uploading with meta:` - при загрузке с параметрами

### Не должно быть:
- Ошибок JavaScript (красные сообщения)
- Предупреждений о missing dependencies
- Ошибок загрузки модулей

---

## 3. Проверьте Network tab

DevTools → Network → перезагрузите страницу:

### Что проверить:
1. **Запросы к сессии:**
   - Должны быть не чаще 1 раза в 15 секунд
   - НЕ должно быть постоянных запросов каждые 1-2 секунды

2. **Запросы при отправке:**
   - Должен быть POST к `/public/scan-sessions/{id}/pages`
   - В FormData должен быть `meta` с `enhancement_mode` и `manual_contour`

3. **Статус ответов:**
   - Все должны быть 200 (OK)
   - НЕ должно быть 500, 502, 404

---

## 4. Проверьте что именно не работает

### Детекция документа:
1. Откройте камеру
2. Наведите на документ
3. В консоли должны быть логи `[scanner] Document detected:`
4. Должна появиться рамка вокруг документа

### Фильтры:
1. Сделайте снимок
2. Выберите фильтр (Standard, Strong, Photo)
3. В консоли должен быть лог `[scanner] PreviewModal: Filter selected`
4. Нажмите "Отправить"
5. В консоли должен быть лог `[scanner] Uploading with meta:` с `enhancement_mode`

### Коррекция границ:
1. Нажмите "Редактировать контур"
2. В консоли должен быть лог `[scanner] PreviewModal: Edit contour button clicked`
3. Должен открыться редактор с 6 точками
4. Перетащите точки
5. Нажмите "Подтвердить"
6. Нажмите "Отправить"
7. В консоли должен быть лог с `manual_contour` в meta

---

## 5. Проверьте backend логи

```bash
cd /opt/HostFlow
docker-compose logs backend --tail 100 -f
```

При отправке документа должны быть логи:
- `INFO: Processing scan session...`
- `INFO: Using enhancement_mode: standard/strong/photo`
- `INFO: Using manual contour for perspective correction` (если был указан)

---

## 6. Если ничего не помогает

### Проверьте версию bundle:
```bash
ls -lh /var/www/hostflow-frontend/assets/index-*.js
```

Должен быть `index-D4BbX2-z.js` с датой 15:05 или позже.

### Пересоберите и задеплойте заново:
```bash
cd /opt/HostFlow/hostflow-frontend
export NODE_OPTIONS=--max-old-space-size=8192
npm run build
sudo rsync -a --delete dist/ /var/www/hostflow-frontend/
sudo systemctl reload nginx
```

### Проверьте что backend работает:
```bash
cd /opt/HostFlow
docker-compose ps backend
docker-compose logs backend --tail 20
```

---

## 7. Диагностическая информация

Если проблемы остаются, соберите:
1. Скриншот консоли браузера (Console tab)
2. Скриншот Network tab (показывающий запросы)
3. Логи backend: `docker-compose logs backend --tail 100`
4. Версию bundle: `ls -lh /var/www/hostflow-frontend/assets/index-*.js`

---

## ✅ Ожидаемое поведение после исправлений:

1. **Страница НЕ обновляется** - запросы к сессии не чаще 1 раза в 15 секунд
2. **Детекция работает** - документ определяется, появляется рамка
3. **Фильтры работают** - выбор фильтра и отправка с правильным `enhancement_mode`
4. **Коррекция границ работает** - редактор открывается, точки draggable, изменения применяются
5. **Отправка работает** - документ загружается и обрабатывается с выбранными параметрами

