import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Modal } from '../../../components/Modal'
import { createReminder } from '../../../api/client'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import { usePlanLimitModal } from '../../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../../utils/friendlyError'

type CandidateQuickTaskModalProps = {
  open: boolean
  onClose: () => void
  candidateId: string
  candidateLabel: string
  t: (key: string, options?: any) => string
}

function defaultDueLocal(): string {
  return new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16)
}

export function CandidateQuickTaskModal({
  open,
  onClose,
  candidateId,
  candidateLabel,
  t,
}: CandidateQuickTaskModalProps) {
  const navigate = useNavigate()
  const planLimitModal = usePlanLimitModal()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [dueAt, setDueAt] = useState(defaultDueLocal)
  const [offsetMin, setOffsetMin] = useState(15)
  const [priority, setPriority] = useState('normal')
  const [busy, setBusy] = useState(false)
  const [errorBanner, setErrorBanner] = useState<{ title: string; detail?: string } | null>(null)

  useEffect(() => {
    if (!open) return
    setTitle('')
    setDescription('')
    setDueAt(defaultDueLocal())
    setOffsetMin(15)
    setPriority('normal')
    setErrorBanner(null)
  }, [open, candidateId])

  const tasksListHref = `${CRM_APP_PATHS.tasks}?tab=tasks&t_status=active&t_entity=candidate&t_q=${encodeURIComponent(
    String(candidateLabel || candidateId || '').slice(0, 80),
  )}`

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    setErrorBanner(null)
    try {
      const due = new Date(dueAt)
      if (Number.isNaN(due.getTime())) {
        setErrorBanner({
          title: t('app.candidates.task_modal.invalid_due', { defaultValue: 'Invalid due date' }),
        })
        return
      }
      const remindAt = new Date(due.getTime() - offsetMin * 60 * 1000)
      await createReminder({
        title: title.trim(),
        description: description.trim() || undefined,
        type: 'custom',
        entity_type: 'candidate',
        entity_id: candidateId,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority,
        channel: 'internal',
      })
      onClose()
    } catch (err: any) {
      const fb = t('app.candidates.task_modal.create_failed', { defaultValue: 'Could not create task' })
      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
        const info = getFriendlyErrorInfo(err, fb, t)
        setErrorBanner({ title: info.title, detail: info.detail })
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t('app.candidates.task_modal.title', { defaultValue: 'New task for candidate' })}
      size="lg"
    >
      <p className="mb-4 text-sm text-slate-600">
        {t('app.candidates.task_modal.subtitle', {
          defaultValue: 'Creates a reminder linked to this candidate. You can manage all tasks on the tasks page.',
        })}
      </p>
      {errorBanner ? (
        <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          <div className="font-medium">{errorBanner.title}</div>
          {errorBanner.detail ? <div className="mt-1 text-xs text-rose-900/90">{errorBanner.detail}</div> : null}
        </div>
      ) : null}
      <form className="space-y-3" onSubmit={submit}>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-600">
            {t('app.reminders.form.title', { defaultValue: 'Task' })}
          </span>
          <input
            className="input w-full"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t('app.reminders.form.title_placeholder', { defaultValue: 'Call candidate, send email…' })}
            autoFocus
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-600">
            {t('app.reminders.form.description', { defaultValue: 'Description' })}
          </span>
          <textarea
            className="input min-h-[4rem] w-full"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t('app.reminders.form.description_placeholder', { defaultValue: 'Optional details…' })}
          />
        </label>
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="block min-w-[12rem] flex-1">
            <span className="mb-1 block text-xs font-medium text-slate-600">
              {t('app.reminders.form.due', { defaultValue: 'Due date' })}
            </span>
            <input type="datetime-local" className="input w-full" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
          </label>
          <label className="block w-full sm:w-auto">
            <span className="mb-1 block text-xs font-medium text-slate-600">
              {t('app.reminders.form.remind_before', { defaultValue: 'Remind before' })}
            </span>
            <select className="input w-full sm:w-36" value={offsetMin} onChange={(e) => setOffsetMin(Number(e.target.value))}>
              <option value={5}>{t('app.candidate_card.reminders.offsets.min5', { defaultValue: '5 min' })}</option>
              <option value={15}>{t('app.candidate_card.reminders.offsets.min15', { defaultValue: '15 min' })}</option>
              <option value={30}>{t('app.candidate_card.reminders.offsets.min30', { defaultValue: '30 min' })}</option>
              <option value={60}>{t('app.candidate_card.reminders.offsets.hour1', { defaultValue: '1 h' })}</option>
            </select>
          </label>
          <label className="block w-full sm:w-auto">
            <span className="mb-1 block text-xs font-medium text-slate-600">
              {t('app.reminders.form.priority', { defaultValue: 'Priority' })}
            </span>
            <select className="input w-full sm:w-36" value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option value="low">{t('app.reminders.priority.low', { defaultValue: 'Low' })}</option>
              <option value="normal">{t('app.reminders.priority.normal', { defaultValue: 'Normal' })}</option>
              <option value="high">{t('app.reminders.priority.high', { defaultValue: 'High' })}</option>
            </select>
          </label>
        </div>
        <div className="flex flex-wrap gap-2 pt-2">
          <button type="submit" className="btn-primary" disabled={busy || !title.trim()}>
            {busy ? t('common.loading') : t('common.actions.save', { defaultValue: 'Save' })}
          </button>
          <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>
            {t('common.actions.cancel', { defaultValue: 'Cancel' })}
          </button>
          <button
            type="button"
            className="btn-secondary ml-auto sm:ml-0"
            onClick={() => {
              onClose()
              navigate(tasksListHref)
            }}
          >
            {t('app.candidates.task_modal.open_tasks_list', { defaultValue: 'Open tasks list' })}
          </button>
        </div>
      </form>
    </Modal>
  )
}
