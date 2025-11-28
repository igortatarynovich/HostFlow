// src/components/Sidebar.tsx
import { Link } from "react-router-dom";
import { settings, resolveApiBase, apiBaseSettings } from "../api/client";

export function Sidebar() {
  // просто показать, откуда сейчас ходят запросы
  const storedApiBase = apiBaseSettings.get();
  const apiBase = storedApiBase ?? resolveApiBase();
  const apiRoot = apiBase.replace(/\/api\/v1\/?$/, "");
  const docsBase =
    import.meta.env.VITE_DOCS_ORIGIN ?? `${apiRoot}/db`;

  return (
    <aside className="h-full w-[200px] min-w-[200px] max-w-[200px] bg-brand-900 text-white p-4 flex flex-col gap-4">
      <div className="text-xl font-bold tracking-wide">HostFlow</div>

      <nav className="flex-1 mt-6 flex flex-col gap-3">
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to="/">Дашборд</Link>
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to="/companies">Компании</Link>
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to="/vacancies">Вакансии</Link>
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to="/app/candidates">Кандидаты</Link>
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to="/pipeline">Канбан</Link>
      </nav>

      <div className="mt-auto pt-6 border-t border-white/10 text-xs opacity-80">
        <div className="font-semibold mb-1">Настройки</div>

        <div className="space-y-3">
          <div>
            <div className="mb-1">API Base</div>
            <input
              className="w-full rounded bg-brand-800 px-2 py-1"
              defaultValue={apiBase}
              placeholder="http://localhost:8000/api/v1"
              onBlur={(e) => {
                const next = e.currentTarget.value.trim();
                if (!next) {
                  apiBaseSettings.clear();
                  window.location.reload();
                  return;
                }
                const normalized = apiBaseSettings.set(next);
                if (!normalized) {
                  alert("Не удалось распознать адрес API. Укажите полный URL, например http://localhost:8000/api/v1");
                  e.currentTarget.value = resolveApiBase();
                  return;
                }
                if (normalized !== apiBase) {
                  window.location.reload();
                }
              }}
            />
            <p className="mt-1 text-[11px] leading-tight text-white/70">
              Измени базовый URL API (оставь пустым для значения по умолчанию).
            </p>
          </div>

          <div>
            <div className="mb-1">Docs Base (read-only)</div>
            <input
              className="w-full rounded bg-brand-800 px-2 py-1 opacity-80"
              value={docsBase}
              readOnly
            />
          </div>

          <div>
            <div className="mb-1">Tenant ID</div>
            <input
              className="w-full rounded bg-brand-800 px-2 py-1"
              defaultValue={settings.get()}
              placeholder="UUID тенанта"
              onBlur={(e) => {
                const v = e.currentTarget.value.trim();
                if (v) {
                  settings.set(v);
                  window.location.reload(); // чтобы новые заголовки сразу применились
                }
              }}
            />
          </div>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
