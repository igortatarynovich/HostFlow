# VAPID Keys для Push-уведомлений

## Что такое VAPID?

**VAPID** (Voluntary Application Server Identification) — это стандарт для идентификации вашего сервера при отправке push-уведомлений через Web Push Protocol.

### Зачем нужны VAPID ключи?

1. **Идентификация сервера** — браузеры проверяют, что уведомления приходят с авторизованного сервера
2. **Безопасность** — предотвращает подделку уведомлений от злоумышленников
3. **Стандарт Web Push** — обязательное требование для отправки push-уведомлений

### Структура ключей

- **PUBLIC KEY (публичный ключ)** — безопасно передавать в браузер, используется для подписки
- **PRIVATE KEY (приватный ключ)** — хранится только на сервере, используется для подписи сообщений

⚠️ **ВАЖНО**: Приватный ключ должен быть секретным! Никогда не коммитьте его в git.

## Как получить VAPID ключи?

### Способ 1: Автоматическая генерация (рекомендуется)

```bash
# Установить библиотеку (в Docker контейнере)
docker compose exec backend pip install py-vapid

# Сгенерировать ключи
docker compose exec backend python scripts/generate_vapid_keys.py
```

Скрипт выведет ключи, которые нужно добавить в `backend/.env`:

```bash
VAPID_PUBLIC_KEY=your_public_key_here
VAPID_PRIVATE_KEY=your_private_key_here
```

### Способ 2: Добавить в requirements.txt

Если хотите сделать это постоянным:

```bash
# Добавить в requirements.txt
echo "py-vapid>=1.9.0" >> backend/requirements.txt

# Пересобрать контейнер
docker compose build backend
docker compose restart backend

# Сгенерировать ключи
docker compose exec backend python scripts/generate_vapid_keys.py
```

### Способ 3: Онлайн-генератор

Можно использовать онлайн-генератор:
- https://web-push-codelab.glitch.me/
- https://vapidkeys.com/

⚠️ **Внимание**: Используйте только проверенные источники для генерации ключей!

### Способ 4: OpenSSL (вручную)

```bash
# Генерировать приватный ключ
openssl ecparam -genkey -name prime256v1 -out private_key.pem

# Извлечь публичный ключ
openssl ec -in private_key.pem -pubout -outform DER | tail -c 65 | base64url > public_key.txt

# Извлечь приватный ключ в формате PKCS8
openssl ec -in private_key.pem -outform DER | tail -c +8 | head -c 32 | base64url > private_key.txt
```

## Настройка в проекте

### 1. Добавить ключи в `.env`

Создайте или отредактируйте `backend/.env`:

```bash
# VAPID keys for Web Push notifications
VAPID_PUBLIC_KEY=your_public_key_here
VAPID_PRIVATE_KEY=your_private_key_here
```

### 2. Перезапустить backend

```bash
docker compose restart backend
```

### 3. Проверить работу

Откройте страницу статуса кандидата и попробуйте подписаться на push-уведомления.

## Как это работает?

1. **Подписка**:
   - Браузер запрашивает публичный ключ с `/api/v1/public/notifications/push/vapid-key`
   - Браузер создает подписку и отправляет её на сервер
   - Сервер сохраняет подписку в `candidate.intake_state["notifications"]["push_subscription"]`

2. **Отправка уведомления**:
   - При изменении статуса документа вызывается `send_candidate_notification()`
   - Если кандидат подписан на push, вызывается `send_push_notification()`
   - Сервер подписывает сообщение приватным ключом и отправляет через Web Push Protocol

## Безопасность

- ✅ Публичный ключ можно безопасно передавать клиентам
- ❌ Приватный ключ должен храниться только на сервере
- ❌ Никогда не коммитьте приватный ключ в git
- ✅ Добавьте `.env` в `.gitignore` (если еще не добавлен)

## Troubleshooting

### Ключи не работают?

1. Проверьте формат ключей (должны быть base64url без padding)
2. Убедитесь, что ключи добавлены в `.env` и контейнер перезапущен
3. Проверьте логи: `docker compose logs backend | grep -i vapid`

### Ошибка "Invalid VAPID key"?

- Убедитесь, что ключи сгенерированы правильно
- Проверьте, что нет лишних пробелов в `.env`
- Попробуйте сгенерировать новые ключи

## Дополнительные ресурсы

- [Web Push Protocol](https://datatracker.ietf.org/doc/html/rfc8030)
- [VAPID Specification](https://datatracker.ietf.org/doc/html/rfc8292)
- [MDN: Push API](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)

