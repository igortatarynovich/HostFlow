cat > connect_docs_module.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"

# --- Проверки наличия ключевых путей ---
test -f "$ROOT/backend/app/main.py" || { echo "Нет backend/app/main.py"; exit 1; }
test -d "$ROOT/docs/labs/docs_module" || { echo "Нет папки docs/labs/docs_module"; exit 1; }
test -f "$ROOT/docs/labs/docs_module/router_db.py" || { echo "Нет docs/labs/docs_module/router_db.py"; exit 1; }

# --- 1) Создаём адаптер: backend/app/external_docs_router.py ---
EXTERNAL="$ROOT/backend/app/external_docs_router.py"
if [ ! -f "$EXTERNAL" ]; then
  cat > "$EXTERNAL" <<'PY'
import os
import sys

# Найдём корень проекта от текущего файла
_THIS_DIR = os.path.dirname(__file__)
_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))  # .../backend/app -> / (корень)
_DOCS_MODULE_PATH = os.path.join(_ROOT, "docs", "labs", "docs_module")

if _DOCS_MODULE_PATH not in sys.path:
    sys.path.insert(0, _DOCS_MODULE_PATH)

# Импортируем APIRouter модуля документов
from router_db import router  # type: ignore
PY
  echo "[+] Создан $EXTERNAL"
else
  echo "[=] Уже есть $EXTERNAL — пропускаю"
fi

# --- 2) Патчим backend/app/main.py: импорт и include_router ---
MAIN="$ROOT/backend/app/main.py"
cp "$MAIN" "$MAIN.bak.docs-module" || true

# а) импорт адаптера, если ещё не добавлен
if ! grep -q "external_docs_router" "$MAIN"; then
  # вставим строку импорта ПОСЛЕ первой строки 'from fastapi import FastAPI' (адаптивно)
  /usr/bin/sed -i '' '/from fastapi import FastAPI/a\
from .external_docs_router import router as documents_db_router
' "$MAIN"
  echo "[+] main.py: добавлен импорт external_docs_router"
else
  echo "[=] main.py: импорт уже есть"
fi

# б) include_router после первой строки с app = FastAPI(…)
if ! grep -q "documents_db_router" "$MAIN"; then
  /usr/bin/sed -i '' '/app = FastAPI/a\
app.include_router(documents_db_router, prefix="/api/v1", tags=["documents-db"])
' "$MAIN"
  echo "[+] main.py: подключён documents_db_router под /api/v1"
else
  echo "[=] main.py: include_router уже есть"
fi

# --- 3) Переписываем фронтовый модуль на /api/v1/db/... ---
FRONT_DOCS_TS="$ROOT/hostflow-frontend/src/modules/documents/documents.ts"
test -f "$FRONT_DOCS_TS" || { echo "Нет $FRONT_DOCS_TS — проверьте путь"; exit 1; }
cp "$FRONT_DOCS_TS" "$FRONT_DOCS_TS.bak.docs-module" || true

cat > "$FRONT_DOCS_TS" <<'TS'
import { api, settings } from "../../api/client"

// Все запросы — через основной axios-клиент `api` (baseURL = http://127.0.0.1:8000/api/v1)
const TENANT = settings.getTenant?.() || import.meta.env.VITE_TENANT_ID

// ====== TYPES ======
export type DocumentType = {
  code: string
  name: string
  description?: string | null
  required?: boolean
}

export type DocumentLastCheck = {
  status: "ok" | "fail" | "pending"
  at?: string | null
  note?: string | null
}

export type CandidateDocument = {
  id: string
  type: string
  title?: string | null
  url?: string | null
  uploaded_at?: string
  last_check?: DocumentLastCheck | null
}

// ====== API ======
// Бьём в новый модуль, подключённый в backend: он вешается на /api/v1 + router(prefix="/db")
// => итого пути: /api/v1/db/document-types, /api/v1/db/candidate/{id}/documents, /api/v1/db/documents/{docId}

export async function getDocumentTypes(): Promise<DocumentType[]> {
  const { data } = await api.get("/db/document-types", {
    headers: { "X-Tenant-Id": TENANT },
  })
  return data
}

export async function listOwnerDocuments(
  ownerId: string,
  opts?: boolean | { include_last_check?: boolean }
): Promise<CandidateDocument[]> {
  const params =
    typeof opts === "boolean" ? { include_last_check: opts } : (opts || {})
  const { data } = await api.get(`/db/candidate/${ownerId}/documents`, {
    params,
    headers: { "X-Tenant-Id": TENANT },
  })
  return data
}

export async function uploadCandidateDocument(
  ownerId: string,
  payload: { file: File; type: string; title?: string }
): Promise<CandidateDocument> {
  const form = new FormData()
  form.append("file", payload.file)
  form.append("type", payload.type)
  if (payload.title) form.append("title", payload.title)

  const { data } = await api.post(`/db/candidate/${ownerId}/documents`, form, {
    headers: {
      "X-Tenant-Id": TENANT,
      "Content-Type": "multipart/form-data",
    },
  })
  return data
}

export async function deleteCandidateDocument(
  documentId: string
): Promise<{ ok: true }> {
  const { data } = await api.delete(`/db/documents/${documentId}`, {
    headers: { "X-Tenant-Id": TENANT },
  })
  return data
}
TS

echo "[+] Перезаписан фронтовый модуль документов на /api/v1/db/*"

echo
echo "Готово. Бэкапы лежат рядом (*.bak.docs-module)."
echo "Теперь перезапусти backend и frontend."
echo
echo "Быстрая проверка после рестарта бэка:"
echo "  curl -i -H 'X-Tenant-ID: 11111111-1111-1111-1111-111111111111' http://127.0.0.1:8000/api/v1/db/document-types"
BASH

chmod +x connect_docs_module.sh
./connect_docs_module.sh