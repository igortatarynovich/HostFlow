// src/components/Sidebar.tsx
import { Link } from "react-router-dom";
import { settings, resolveApiBase, apiBaseSettings } from "../api/client";
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { useI18n } from "../i18n";

export function Sidebar() {
  const { t } = useI18n();
  // просто показать, откуда сейчас ходят запросы
  const storedApiBase = apiBaseSettings.get();
  const apiBase = storedApiBase ?? resolveApiBase();
  const apiRoot = apiBase.replace(/\/api\/v1\/?$/, "");
  const docsBase =
    import.meta.env.VITE_DOCS_ORIGIN ?? `${apiRoot}/db`;

  return (
    <aside className="h-full w-[200px] min-w-[200px] max-w-[200px] bg-brand-900 text-white p-4 flex flex-col gap-4">
      <img
        src="/logo_hf_white.svg"
        alt="HostFlow"
        className="h-9 w-auto"
        loading="lazy"
      />

      <nav className="flex-1 mt-6 flex flex-col gap-3">
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to="/">{t('app.sidebar.nav.dashboard')}</Link>
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to="/companies">{t('app.sidebar.nav.companies')}</Link>
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to="/vacancies">{t('app.sidebar.nav.vacancies')}</Link>
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to={CRM_APP_PATHS.candidates}>{t('app.sidebar.nav.candidates')}</Link>
        <Link className="px-3 py-2 rounded hover:bg-brand-800" to="/pipeline">{t('app.sidebar.nav.kanban')}</Link>
      </nav>

      <div className="mt-auto pt-6 border-t border-white/10 text-xs opacity-80">
        <div className="font-semibold mb-1">{t('app.sidebar.nav.settings')}</div>

        <div className="space-y-3">
          <div>
            <div className="mb-1">{t('app.sidebar.settings.api_base', { defaultValue: 'API Base' })}</div>
            <input
              className="w-full rounded bg-brand-800 px-2 py-1"
              defaultValue={apiBase}
              placeholder={t('app.sidebar.settings.api_base_placeholder', { defaultValue: 'http://localhost:8000/api/v1' })}
              onBlur={(e) => {
                const next = e.currentTarget.value.trim();
                if (!next) {
                  apiBaseSettings.clear();
                  window.location.reload();
                  return;
                }
                const normalized = apiBaseSettings.set(next);
                if (!normalized) {
                  alert(t('app.sidebar.settings.api_invalid'));
                  e.currentTarget.value = resolveApiBase();
                  return;
                }
                if (normalized !== apiBase) {
                  window.location.reload();
                }
              }}
            />
            <p className="mt-1 text-[11px] leading-tight text-white/70">
              {t('app.sidebar.settings.api_hint')}
            </p>
          </div>

          <div>
            <div className="mb-1">{t('app.sidebar.settings.docs_base', { defaultValue: 'Docs Base (read-only)' })}</div>
            <input
              className="w-full rounded bg-brand-800 px-2 py-1 opacity-80"
              value={docsBase}
              readOnly
            />
          </div>

          <div>
            <div className="mb-1">{t('app.sidebar.settings.tenant_id', { defaultValue: 'Tenant ID' })}</div>
            <input
              className="w-full rounded bg-brand-800 px-2 py-1"
              defaultValue={settings.get()}
              placeholder={t('app.sidebar.settings.tenant_placeholder', { defaultValue: 'Tenant UUID' })}
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
