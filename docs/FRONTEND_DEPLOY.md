# Деплой фронтенда (почему «нет изменений»)

## Типовая последовательность с сервера (`/opt/HostFlow`)

Используй везде **`docker compose`** (V2), не `docker-compose`, если плагин установлен.

```bash
cd /opt/HostFlow

# Бэкенд (если менялся код backend / Dockerfile / нужен свежий образ)
docker compose up -d --build backend

# Фронт: пересобрать dist на хосте (Caddy и backend читают ./hostflow-frontend/dist с диска)
(cd hostflow-frontend && npm run build)

# Подхватить новый index.html и ассеты в Caddy (bind-mount обновляется сразу, restart — на всякий случай)
docker compose restart caddy
```

- Чисто **фронтовые** правки: достаточно **`npm run build` + `docker compose restart caddy`**. `--build backend` не обязателен.
- Заход в UI по **домену за Caddy** → смотри ответы Caddy. Заход **напрямую на порт backend** → тоже `/app/public` из того же `dist`, перезапуск backend обычно не нужен из‑за volume.

Продакшен обычно отдаёт UI так:

1. **`docker-compose.yml`**: Caddy монтирует **`./hostflow-frontend/dist` → `/var/www/hostflow-frontend`** и раздаёт статику (см. `Caddyfile`).
2. Бэкенд тоже монтирует **`./hostflow-frontend/dist` → `/app/public`** для раздачи того же SPA с порта API (если заходишь напрямую на backend).

Если после правок «ничего не меняется»:

## Обязательно пересобрать `dist`

```bash
cd hostflow-frontend
npm ci   # при необходимости
npm run build
```

Убедиться, что в `dist/assets/index-*.js` есть свежая логика (пример):

```bash
rg "workPanelOpen|data-hf-ui|candidates-flex-rail-v4" dist/assets/index-*.js
```

## Кеш браузера

Раньше весь SPA-блок мог кешироваться слишком агрессивно: старый **`index.html`** → старый путь к **`index-xxxxx.js`**.

В `Caddyfile` для **`/assets/*`** включён долгий кеш, для остального SPA — **`Cache-Control: no-cache, no-store, must-revalidate`**.

Если фронт отдаёт **nginx** (например `deploy/nginx/hostflow.conf`), нужно то же правило: отдельный **`location /assets/`** с **`immutable`**, а для **`location /`** (SPA fallback на **`index.html`**) — **`no-cache, no-store, must-revalidate`**. Без этого браузер или CDN может отдавать старый **`index.html`** → в консоли **`Failed to fetch dynamically import module`** и **404** на **`routeBundle*.js`**.

После смены `Caddyfile`: `docker compose up -d caddy` (или полный restart стека).

### Ошибка в консоли: `Failed to fetch dynamically imported module` + 404 на `routeBundle*.js`

Это почти всегда **рассинхрон после деплоя**: в памяти вкладки остался старый entry (`index-….js`), он тянет **старый** хэш чанка (`routeBundleInvoices-….js`), а на диске после `npm run build` уже **другие** имена файлов — чанк 404, ленивый импорт падает.

**Клиентское смягчение (в репо):** `src/utils/staleChunkReload.ts` + вызов из **`main.tsx`** — при такой ошибке выполняется **одна** перезагрузка страницы (не чаще чем раз в **10 с** по `sessionStorage`), чтобы подтянуть свежий **`index.html`**. Это не заменяет правильные **Cache-Control** для HTML: если CDN всё ещё отдаёт старый shell, после одной лишней попытки пользователю нужен **жёсткий сброс кеша** или правило **Bypass** для HTML.

Что сделать:

1. **Жёсткое обновление** страницы: Ctrl+Shift+R (или закрыть вкладку и открыть снова с того же origin).
2. На сервере: убедиться, что в `hostflow-frontend/dist/assets/` есть файл, на который ссылается текущий `dist/index.html`, и что Caddy отдаёт тот же каталог (`docker compose restart caddy`).
3. Если перед сайтом стоит **Cloudflare / другой CDN** — для `index.html` (и корня SPA) отключить агрессивный кеш или задать **Bypass / no cache** для HTML, иначе клиенты могут получать старый shell с ссылками на несуществующие чанки.

Проверка заголовков:

```bash
curl -sI "https://ВАШ_ДОМЕН/index.html" | grep -i cache
```

## Проверка в браузере

На странице списка кандидатов корневой блок разметки должен содержать:

`data-hf-ui="candidates-flex-rail-v4-scrollfix"`

(Инспектор → выбрать корневой контейнер страницы кандидатов.)

Если атрибута нет — открыт **старый** бандл или не та среда.
