# Troubleshooting hostflow.cc

## Изменения во фронте не видны на hostflow.cc (старый UI)

**Причина:** для домена статика отдаёт **контейнер `caddy`** из каталога `/var/www/hostflow-frontend` (см. `Caddyfile`). Образ Caddy собирается с **`COPY hostflow-frontend/dist`**. Пересборка **только `backend`** не обновляет JS/CSS.

**Что сделать:**

В `docker-compose.yml` сервис **caddy** монтирует `./hostflow-frontend/dist` → `/var/www/hostflow-frontend`. Достаточно:

```bash
cd /path/to/HostFlow/hostflow-frontend && npm run build
cd .. && docker compose up -d caddy
# или: docker compose restart caddy
```

**Важно:** одна только команда `docker compose restart caddy` **без bind-mount** dist в compose **не подхватывает** новый билд — тогда статика остаётся той, что была **запечена** в образ при `docker compose build caddy`. В этом случае после `npm run build` нужно:

```bash
docker compose build caddy && docker compose up -d caddy
```

Проверка: в DevTools → Network откройте любой `index-*.js` — время ответа и размер должны измениться после деплоя. Для `index.html` в Caddy уже выставлен `no-cache`.

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
