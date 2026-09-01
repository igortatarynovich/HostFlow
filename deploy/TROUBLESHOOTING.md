# Troubleshooting hostflow.cc

## Изменения во фронте не видны на hostflow.cc (старый UI)

**Причины (часто вместе):**

1. Выкладка шла через `rebuild-frontend.sh`, который rsync'ил в **хостовый** `/var/www/hostflow-frontend`. Caddy этот путь **не монтирует**. Он отдаёт `./hostflow-frontend/dist` из checkout (bind-mount на контейнерный `/var/www/hostflow-frontend`).
2. Сделали `git pull` / поправили `src/`, но не пересобрали SPA. `dist` gitignored.
3. Браузер держит старый `index.html` → старые hashed chunks.

**Что сделать:**

```bash
cd /opt/HostFlow
make deploy-live
# только фронт: bash rebuild-frontend.sh
```

Процедура и проверки: [`docs/FRONTEND_DEPLOY.md`](../docs/FRONTEND_DEPLOY.md).

**Важно:** `docker compose restart caddy` без новой сборки в `hostflow-frontend/dist` ничего не меняет. Образ Caddy с `COPY dist` используется только если bind-mount отсутствует — тогда нужен `docker compose build caddy && docker compose up -d caddy`. На текущем стеке bind-mount есть; правильный publish — `deploy-live.sh`.

Проверка: `curl -sk https://hostflow.cc/build.json` — `built_at` должен совпасть с только что закончившимся деплоем. В DevTools → Network откройте любой `index-*.js` — время ответа и размер должны измениться. Для `index.html` в Caddy уже выставлен `no-cache`.

---

## 502 Bad Gateway на /api/*, /api/v1/auth/login, whoami-verify, users/me, uploads

**Причина:** Nginx не получает ответ от бэкенда на `http://127.0.0.1:8000`. Код приложения здесь ни при чём — падает связка «прокси → бэкенд».

### Что проверить на сервере hostflow.cc

1. **Бэкенд слушает порт 8000**

   ```bash
   # Если бэкенд в Docker:
   cd /path/to/HostFlow
   docker compose ps
   docker compose logs backend --tail 100

   # Локально порт:
   curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health
   # Ожидается 200. Если connection refused — процесс не запущен или не на 8000.
   ```

2. **Перезапуск бэкенда**

   ```bash
   docker compose restart backend
   # или, если без Docker:
   # перезапустить systemd/supervisor unit, который поднимает uvicorn
   ```

3. **Логи**

   - Nginx: `sudo tail -100 /var/log/nginx/error.log` — часто видно «upstream timed out» или «connection refused».
   - Бэкенд: `docker compose logs backend` — падения, исключения при старте, ошибки БД/Redis.

4. **База и Redis**

   Если бэкенд падает при первом запросе из‑за БД/Redis:

   ```bash
   docker compose ps
   docker compose logs db --tail 50
   docker compose logs redis --tail 20
   ```

5. **Конфиг nginx**

   Убедитесь, что используется актуальный `deploy/nginx/hostflow.conf`: прокси в `location /api/` должен смотреть на `http://127.0.0.1:8000/api/`.

После исправления (запуск/рестарт бэкенда, починка БД) 502 с `/api/*` и логина должна пропасть без изменений в коде.
