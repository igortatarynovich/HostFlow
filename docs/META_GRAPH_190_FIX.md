# Решение ошибки GRAPH_190 в Meta Leads

## Проблема

Ошибка `GRAPH_190` означает **"Invalid or expired token"** - недействительный или истекший токен доступа к Graph API от Meta/Facebook.

**Текущая ситуация:**
- 143 лида с ошибкой GRAPH_190 из 734 всего
- Токены доступа истекли или стали недействительными

## Решение

### Шаг 1: Получение нового Page Access Token

#### Вариант A: Через Graph API Explorer (рекомендуется)

1. Откройте [Graph API Explorer](https://developers.facebook.com/tools/explorer/)

2. Выберите приложение:
   - **App**: `HostFlow Leads`
   - **App ID**: `1102404865044655`

3. Настройте права доступа:
   - Нажмите "Get Token" → "Get User Access Token"
   - Выберите права:
     - `pages_read_engagement`
     - `pages_manage_metadata`
     - `pages_show_list`
     - `leads_retrieval`
   - Нажмите "Generate Access Token"

4. Обменяйте на long-lived token:
   ```
   GET /oauth/access_token?
     grant_type=fb_exchange_token&
     client_id=1102404865044655&
     client_secret=84f2797ffc4cfe3befc36b2e23e4913b&
     fb_exchange_token={ВАШ_USER_ACCESS_TOKEN}
   ```
   
   Или через Graph API Explorer:
   - Выберите "GET"
   - Endpoint: `/oauth/access_token`
   - Добавьте параметры:
     - `grant_type`: `fb_exchange_token`
     - `client_id`: `1102404865044655`
     - `client_secret`: `84f2797ffc4cfe3befc36b2e23e4913b`
     - `fb_exchange_token`: ваш User Access Token

5. Получите Page Access Token:
   ```
   GET /{page-id}?fields=access_token
   ```
   
   Где `{page-id}` - это ID страницы Facebook:
   - **Poltrakt**: `484113398123847`
   - **Citronex**: `259905353877064`

#### Вариант B: Через Facebook Business Manager

1. Зайдите в [Facebook Business Manager](https://business.facebook.com/)
2. Settings → Business Settings → System Users
3. Создайте или выберите System User
4. Назначьте права на страницу
5. Сгенерируйте токен с правами `leads_retrieval`

### Шаг 2: Обновление токена в HostFlow

#### Через админку (UI):

1. Зайдите в HostFlow → **Settings → Integrations → Meta Leads**
2. Найдите нужный credential (Poltrakt Leads или Citronex Leads)
3. Нажмите "Edit" или "Update"
4. Вставьте новый `access_token` в поле "Access Token"
5. Сохраните изменения

#### Через API:

```bash
# Получите credential_id из админки или через скрипт check_meta_tokens.py

curl -X PATCH \
  "https://hostflow.cc/api/v1/admin/meta-leads/credentials/{credential_id}" \
  -H "Authorization: Bearer {YOUR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "НОВЫЙ_PAGE_ACCESS_TOKEN"
  }'
```

#### Через скрипт (если есть прямой доступ к БД):

```python
# Можно создать скрипт для обновления через admin_service.update_credential
```

### Шаг 3: Перезапуск обработки лидов с ошибкой

После обновления токенов перезапустите обработку лидов:

```bash
cd /opt/HostFlow
docker compose exec backend python backend/scripts/retry_meta_leads.py \
  --tenant 11111111-1111-1111-1111-111111111111 \
  --status failed
```

Или только лиды с GRAPH_190:

```bash
# Сначала найдите ID лидов с ошибкой
docker compose exec db psql -U hostflow -d hostflow -c \
  "SELECT id FROM leads WHERE tenant_id = '11111111-1111-1111-1111-111111111111' AND error = 'GRAPH_190' LIMIT 50;"

# Затем перезапустите их
docker compose exec backend python backend/scripts/retry_meta_leads.py \
  --tenant 11111111-1111-1111-1111-111111111111 \
  --lead <lead_id_1> --lead <lead_id_2> ...
```

## Проверка

После обновления токенов проверьте:

```bash
docker compose exec backend python backend/scripts/check_meta_tokens.py \
  --tenant 11111111-1111-1111-1111-111111111111
```

## Предотвращение в будущем

1. **Используйте long-lived tokens** - они действуют до 60 дней
2. **Настройте автоматическое обновление** через Facebook Business Manager
3. **Мониторьте `last_verified_at`** в credentials - если он старый, токен может быть недействителен
4. **Регулярно проверяйте ошибки** через скрипт `check_meta_tokens.py`

## Дополнительная информация

- [Документация Meta Leads Setup](../specs/integrations/meta_leads_setup.md)
- [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
- [Facebook Business Manager](https://business.facebook.com/)

