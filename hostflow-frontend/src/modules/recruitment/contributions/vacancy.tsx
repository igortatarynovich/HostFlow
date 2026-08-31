import { useCallback, useEffect, useState } from 'react'
import { confirmRecruitmentApplicationVacancy } from '../../../api/applications'
import { listVacancies } from '../../../api/client'
import { Button } from '../../../components/ui/Button'
import { useToast } from '../../../components/Toast'
import { useI18n } from '../../../i18n'
import { getFriendlyErrorInfo } from '../../../utils/friendlyError'
import type { WorkspaceCapabilityRenderContext } from '../../../platform/workspace-capability/renderContext'

export function RecruitmentVacancyContribution({
  application,
  patching,
  onRefresh,
}: WorkspaceCapabilityRenderContext) {
  const { notify } = useToast()
  const { t } = useI18n()
  const [vacancies, setVacancies] = useState<Array<{ id: string; title: string }>>([])
  const [selectedVacancyId, setSelectedVacancyId] = useState(String(application?.extensions?.vacancy_id || ''))
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    void listVacancies({ limit: 30 }).then((res) => {
      if (cancelled) return
      const items = Array.isArray(res) ? res : (res as { items?: Array<{ id: string; title?: string }> })?.items ?? []
      setVacancies(items.map((vacancy) => ({ id: String(vacancy.id), title: String(vacancy.title || vacancy.id) })))
    })
    return () => {
      cancelled = true
    }
  }, [])

  const bind = useCallback(async () => {
    if (!application || !selectedVacancyId || busy || patching) return
    setBusy(true)
    try {
      await confirmRecruitmentApplicationVacancy(application.id, { vacancy_id: selectedVacancyId })
      notify({ title: t('app.recruitment.contributions.bound'), variant: 'success' })
      onRefresh()
    } catch (err: unknown) {
      const info = getFriendlyErrorInfo(err, t('app.recruitment.contributions.bind_failed'), t)
      notify({ title: info.title, variant: 'error' })
    } finally {
      setBusy(false)
    }
  }, [application, busy, notify, onRefresh, patching, selectedVacancyId, t])

  return (
    <section className="space-y-2" data-capability-id="recruitment.vacancy">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.recruitment.contributions.search')}
      </p>
      <select value={selectedVacancyId} onChange={(event) => setSelectedVacancyId(event.target.value)} className="input">
        <option value="">{t('app.recruitment.contributions.pick_search')}</option>
        {vacancies.map((vacancy) => (
          <option key={vacancy.id} value={vacancy.id}>
            {vacancy.title}
          </option>
        ))}
      </select>
      <Button variant="secondary" size="sm" disabled={!selectedVacancyId || patching || busy} onClick={() => void bind()}>
        {t('app.recruitment.contributions.bind_search')}
      </Button>
    </section>
  )
}
