import { IconPlus } from '@tabler/icons-react'
import { useOwnCompanyWorkspace } from '../../hooks/useOwnCompanyWorkspace'
import { useI18n } from '../../i18n'

/** Own-company scope switcher (moved from top bar into the left rail). */
export function SidebarOwnCompanySection() {
  const { t } = useI18n()
  const oc = useOwnCompanyWorkspace()

  if (!oc.visible) return null

  return (
    <>
      <div className="mb-3 min-w-0 overflow-hidden rounded-lg border border-white/15 bg-white/5 px-2.5 py-2">
        <div className="flex flex-wrap items-center gap-1.5">
          {oc.ownCompanies.length > 0 ? (
            <select
              className="min-w-0 max-w-full flex-1 rounded-md border border-white/20 bg-white/10 px-1.5 py-1 text-[11px] font-medium text-white outline-none focus-visible:ring-2 focus-visible:ring-white/40"
              aria-label={t('app.topbar.own_company')}
              value={oc.activeOwnCompanyId || ''}
              onChange={(e) => oc.selectCompany(e.target.value)}
            >
              {oc.ownCompanies.map((c) => (
                <option key={c.id} value={c.id} className="text-slate-900">
                  {c.name}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-xs font-medium text-white/50">—</span>
          )}
          {oc.canAddOwnCompany ? (
            <button
              type="button"
              disabled={oc.atPlanLimit || oc.createBusy}
              title={
                oc.atPlanLimit ? t('app.topbar.own_company_limit_tooltip') : t('app.topbar.own_company_create')
              }
              aria-label={t('app.topbar.own_company_create')}
              className={[
                'inline-flex h-7 w-7 shrink-0 items-center justify-center rounded border transition',
                oc.atPlanLimit || oc.createBusy
                  ? 'cursor-not-allowed border-white/10 text-white/30'
                  : 'border-white/25 text-white hover:bg-white/10',
              ].join(' ')}
              onClick={() => {
                oc.setNewName('')
                oc.setCreateOpen(true)
              }}
            >
              <IconPlus size={16} stroke={2} />
            </button>
          ) : null}
        </div>
      </div>

      {oc.createOpen ? (
        <div
          className="fixed inset-0 z-[200] flex items-start justify-center bg-black/50 p-4 pt-24 sm:pt-32"
          role="dialog"
          aria-modal="true"
          aria-labelledby="hf-sidebar-own-company-create-title"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) oc.setCreateOpen(false)
          }}
        >
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 text-slate-900 shadow-2xl">
            <h2 id="hf-sidebar-own-company-create-title" className="text-lg font-semibold">
              {t('app.topbar.own_company_create_title')}
            </h2>
            <p className="mt-1 text-sm text-slate-500">{t('app.topbar.own_company_create_blurb')}</p>
            <label className="mt-4 block text-sm font-medium text-slate-700">
              {t('app.topbar.own_company_create_name')}
              <input
                autoFocus
                className="input mt-1 w-full"
                value={oc.newName}
                onChange={(e) => oc.setNewName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') oc.setCreateOpen(false)
                  if (e.key === 'Enter') void oc.submitCreate()
                }}
              />
            </label>
            {oc.atPlanLimit ? (
              <p className="mt-3 text-sm text-amber-800">{t('app.topbar.own_company_limit_tooltip')}</p>
            ) : null}
            <div className="mt-6 flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
                onClick={() => oc.setCreateOpen(false)}
              >
                {t('common.actions.cancel')}
              </button>
              {oc.canOpenBilling ? (
                <button
                  type="button"
                  className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 transition hover:bg-slate-50"
                  onClick={oc.openBilling}
                >
                  {t('app.topbar.own_company_open_billing')}
                </button>
              ) : null}
              <button
                type="button"
                disabled={oc.createBusy || !oc.newName.trim() || oc.atPlanLimit}
                className="rounded-md bg-brand-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                onClick={() => void oc.submitCreate()}
              >
                {oc.createBusy ? t('common.loading') : t('app.topbar.own_company_create_submit')}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
