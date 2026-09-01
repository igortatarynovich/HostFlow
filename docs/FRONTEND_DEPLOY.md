# Деплой фронтенда (почему «нет изменений»)

Каноническая команда на live-хосте (`/opt/HostFlow`, `hostflow.cc`):

```bash
cd /opt/HostFlow
make deploy-live
# эквивалент: bash scripts/deploy/deploy-live.sh
```

Это **не** RB-1 из [индекса runbook](runbooks/README.md) (тот путь ещё не выкатывает retained artefacts на этот стек). Live compose по-прежнему исполняет рабочее дерево. Скрипт закрывает дыры, из‑за которых фиксы «отваливались» после деплоя:

1. **Фронт.** Caddy bind-mount'ит `./hostflow-frontend/dist` → контейнерный `/var/www/hostflow-frontend`. Хостовый каталог `/var/www/hostflow-frontend` **не служит**. Старый `rebuild-frontend.sh` rsync'ил туда и создавал иллюзию выкладки. Сейчас сборка идёт во временный каталог, затем `rsync` в `hostflow-frontend/dist` (inode bind-mount не ломается).
2. **Бэкенд.** `uvicorn` в compose **без `--reload`**. `git pull` сам по себе не подхватывает Python: нужен recreate контейнера. Скрипт делает `docker compose up -d --force-recreate --no-deps backend` (и `arq-worker`, если он запущен).
3. **Идентичность.** `GET /build` и `dist/build.json` получают `HOSTFLOW_REVISION` / `HOSTFLOW_BUILT_AT` в момент выкладки. Если оба `unknown` — деплой не прошёл через этот скрипт.

`rebuild-frontend.sh` остаётся обёрткой: `deploy-live.sh --frontend-only`.

Опции: `make deploy-live ARGS='--pull'` (ff-only с `origin/integration/release-product-a-b`, только на чистом дереве), `--build-backend`, `--skip-frontend`, `--skip-migrate`.

Используй везде **`docker compose`** (V2), не `docker-compose`.

Продакшен отдаёт UI так:

1. **`docker-compose.yml`**: Caddy монтирует **`./hostflow-frontend/dist` → `/var/www/hostflow-frontend`** и раздаёт статику (см. `Caddyfile`).
2. Бэкенд тоже монтирует **`./hostflow-frontend/dist` → `/app/public`** для раздачи того же SPA с порта API (если заходишь напрямую на backend).

Если после правок «ничего не меняется»:

## Обязательно пересобрать `dist`

Не `git pull` и не `docker compose restart caddy` сами по себе. Нужен `make deploy-live` (или хотя бы `--frontend-only`). Убедиться, что в `dist/assets/index-*.js` есть свежая логика (пример):

```bash
rg "workPanelOpen|data-hf-ui|candidates-flex-rail-v4" dist/assets/index-*.js
```

Проверка идентичности:

```bash
curl -sS http://127.0.0.1:8000/build
curl -sk https://hostflow.cc/build.json
```

`GET https://hostflow.cc/build` должен быть JSON процесса, не `index.html`.

## Кеш браузера

Раньше весь SPA-блок мог кешироваться слишком агрессивно: старый **`index.html`** → старый путь к **`index-xxxxx.js`**.

В `Caddyfile` для **`/assets/*`** включён долгий кеш, для остального SPA — **`Cache-Control: no-cache, no-store, must-revalidate`**.

Если фронт отдаёт **nginx** (например `deploy/nginx/hostflow.conf`), нужно то же правило: отдельный **`location /assets/`** с **`immutable`**, а для **`location /`** (SPA fallback на **`index.html`**) — **`no-cache, no-store, must-revalidate`**. Без этого браузер или CDN может отдавать старый **`index.html`** → в консоли **`Failed to fetch dynamically import module`** и **404** на **`routeBundle*.js`**.

После смены `Caddyfile`: `docker compose up -d caddy` (или полный restart стека). `make deploy-live` перезапускает Caddy сам.

### Ошибка в консоли: `Failed to fetch dynamically imported module` + 404 на `routeBundle*.js`

Это почти всегда **рассинхрон после деплоя**: в памяти вкладки остался старый entry (`index-….js`), он тянет **старый** хэш чанка (`routeBundleInvoices-….js`), а на диске после сборки уже **другие** имена файлов — чанк 404, ленивый импорт падает.

**Клиентское смягчение (в репо):** `src/utils/staleChunkReload.ts` + вызов из **`main.tsx`** — при такой ошибке выполняется **одна** перезагрузка страницы (не чаще чем раз в **10 с** по `sessionStorage`), чтобы подтянуть свежий **`index.html`**. Это не заменяет правильные **Cache-Control** для HTML: если CDN всё ещё отдаёт старый shell, после одной лишней попытки пользователю нужен **жёсткий сброс кеша** или правило **Bypass** для HTML.

Что сделать:

1. **Жёсткое обновление** страницы: Ctrl+Shift+R (или закрыть вкладку и открыть снова с того же origin).
2. На сервере: убедиться, что в `hostflow-frontend/dist/assets/` есть файл, на который ссылается текущий `dist/index.html`, и что Caddy отдаёт тот же каталог.
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
