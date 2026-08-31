import { useState } from 'react'
import { assignRecruitmentApplication } from '../../../api/applications'
import { Button } from '../../../components/ui/Button'
import { useToast } from '../../../components/Toast'
import { useI18n } from '../../../i18n'
import { getFriendlyErrorInfo } from '../../../utils/friendlyError'
import type { WorkspaceCapabilityRenderContext } from '../../../platform/workspace-capability/renderContext'

export function RecruitmentAssigneeContribution({
  application,
  patching,
  onRefresh,
}: WorkspaceCapabilityRenderContext) {
  const { notify } = useToast()
  const { t } = useI18n()
  const [assigneeId, setAssigneeId] = useState(application?.assignee_id || '')
  const [busy, setBusy] = useState(false)

  return (
    <section className="space-y-2" data-capability-id="recruitment.assignee">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.recruitment.contributions.assignee')}
      </p>
      <div className="flex gap-2">
        <input
          value={assigneeId}
          onChange={(event) => setAssigneeId(event.target.value)}
          className="input flex-1"
          placeholder={t('app.recruitment.contributions.user_id_placeholder')}
        />
        <Button
          variant="primary"
          size="sm"
          disabled={!assigneeId.trim() || patching || busy}
          onClick={() => {
            void (async () => {
              if (!application) return
              setBusy(true)
              try {
                await assignRecruitmentApplication(application.id, { assignee_id: assigneeId.trim() })
                notify({ title: t('app.recruitment.contributions.assigned'), variant: 'success' })
                onRefresh()
              } catch (err: unknown) {
                const info = getFriendlyErrorInfo(err, t('app.recruitment.contributions.assign_failed'), t)
                notify({ title: info.title, variant: 'error' })
              } finally {
                setBusy(false)
              }
            })()
          }}
        >
          {t('app.recruitment.contributions.assign')}
        </Button>
      </div>
    </section>
  )
}
