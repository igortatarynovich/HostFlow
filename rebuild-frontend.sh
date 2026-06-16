#!/bin/bash
set -e

echo "🔨 Сборка фронтенда..."
cd hostflow-frontend
npm run build
cd ..

echo "📄 Проверка legal документов в dist..."
if [ -d "hostflow-frontend/dist/legal" ]; then
  ls -1 hostflow-frontend/dist/legal >/dev/null
else
  echo "⚠️  Не найден hostflow-frontend/dist/legal. Проверьте наличие legal HTML файлов."
fi

echo "📦 Публикация в /var/www/hostflow-frontend (Caddy root)..."
rsync -a --delete hostflow-frontend/dist/ /var/www/hostflow-frontend/

echo "🔄 Перезапуск Caddy..."
docker-compose restart caddy

echo "✅ Готово! Фронтенд собран и Caddy перезапущен."
