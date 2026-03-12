import { memo, useCallback, useMemo, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { enUS, pl, ru } from 'date-fns/locale'
import type { ReminderRecord } from '../../api/types'
import { useI18n } from '../../i18n'

interface CandidateRemindersSectionProps {
  candidateId: string
  reminders: ReminderRecord[]
  remindersLoading: boolean
  remindersError: string | null
  reminderBusy: string | null
  onReminderCreate: () => void
  onReminderComplete: (id: string) => void
  onReminderSnooze: (id: string, minutes: number) => void
  onReminderTitleChange: (title: string) => void
  onReminderDueAtChange: (date: string) => void
  onReminderOffsetChange: (offset: number) => void
  reminderTitle: string
  reminderDueAt: string
  reminderOffset: number
  embedded?: boolean
}

function CandidateRemindersSection({
  reminders,
  remindersLoading,
  remindersError,
  reminderBusy,
  onReminderCreate,
  onReminderComplete,
  onReminderSnooze,
  onReminderTitleChange,
  onReminderDueAtChange,
  onReminderOffsetChange,
  reminderTitle,
  reminderDueAt,
  reminderOffset,
  embedded = false,
}: CandidateRemindersSectionProps) {
  const { t, locale } = useI18n()
  const [open, setOpen] = useState(false)
  const dateFnsLocale = useMemo(() => (locale === 'ru' ? ru : locale === 'pl' ? pl : enUS), [locale])

  const formatReminderDate = useCallback(
    (value?: string | null) => {
      if (!value) return t('app.candidate_card.reminders.date_placeholder')
      const parsed = Date.parse(value)
      if (Number.isNaN(parsed)) {
        return value
      }
      return new Date(parsed).toLocaleString(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    },
    [locale, t]
  )

  const translateReminderStatus = useCallback(
    (status?: string | null) => {
      const normalized = (status || '').trim().toLowerCase()
      if (!normalized) return t('app.candidate_card.reminders.statuses.pending')
      return t(`app.candidate_card.reminders.statuses.${normalized}`, { defaultValue: status || '' })
    },
    [t]
  )

  const fullContent = (
    <div className="space-y-4 min-w-0">
      <div className="flex flex-col gap-2 min-w-0">
        <input
          className="input w-full min-w-0"
          placeholder={t('app.candidate_card.reminders.placeholder')}
          value={reminderTitle}
          onChange={(e) => onReminderTitleChange(e.target.value)}
        />
        <div className="flex flex-col gap-2 min-w-0 sm:flex-row sm:flex-wrap sm:items-center">
          <input
            type="datetime-local"
            className="input w-full min-w-0 flex-1 sm:min-w-[180px]"
            value={reminderDueAt}
            onChange={(e) => onReminderDueAtChange(e.target.value)}
          />
          <select
            className="input w-full min-w-0 sm:w-auto sm:min-w-[100px]"
            value={reminderOffset}
            onChange={(e) => onReminderOffsetChange(Number(e.target.value))}
          >
            <option value={5}>{t('app.candidate_card.reminders.offsets.min5')}</option>
            <option value={15}>{t('app.candidate_card.reminders.offsets.min15')}</option>
            <option value={30}>{t('app.candidate_card.reminders.offsets.min30')}</option>
            <option value={60}>{t('app.candidate_card.reminders.offsets.hour1')}</option>
          </select>
          <button type="button" className="btn-primary w-full sm:w-auto shrink-0" onClick={onReminderCreate} disabled={!reminderTitle}>
            {t('app.candidate_card.reminders.create')}
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-dashed border-slate-200 bg-white/70 p-3">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{t('app.candidate_card.reminders.upcoming')}</span>
          {remindersLoading && <span className="text-slate-400">{t('common.loading')}</span>}
        </div>
        {reminders.length === 0 && !remindersLoading ? (
          <p className="mt-2 text-xs text-slate-500">{t('app.candidate_card.reminders.empty')}</p>
        ) : (
          <ul className="mt-2 space-y-2 max-h-[40vh] overflow-auto">
            {reminders.map((r) => (
              <li key={r.id} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                <p className="text-sm font-semibold text-slate-900">
                  {r.title || t('app.candidate_card.reminders.untitled')}
                </p>
                <p className="text-xs text-slate-500">
                  {t('app.candidate_card.reminders.status_label')}: {translateReminderStatus(r.status)}
                </p>
                <div className="mt-1 text-xs text-slate-600">
                  <div>
                    {t('app.candidate_card.reminders.due')}: {formatReminderDate(r.due_at)}
                  </div>
                  <div>
                    {t('app.candidate_card.reminders.remind')}: {r.remind_at
                      ? formatDistanceToNow(new Date(r.remind_at), { addSuffix: true, locale: dateFnsLocale })
                      : t('app.candidate_card.reminders.date_placeholder')}
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-primary btn-xs disabled:opacity-60"
                    onClick={() => onReminderComplete(r.id)}
                    disabled={reminderBusy === r.id}
                  >
                    {reminderBusy === r.id ? t('common.loading') : t('app.candidate_card.reminders.complete')}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-xs disabled:opacity-60"
                    onClick={() => onReminderSnooze(r.id, 15)}
                    disabled={reminderBusy === r.id}
                  >
                    {t('app.candidate_card.reminders.snooze_15')}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-xs disabled:opacity-60"
                    onClick={() => onReminderSnooze(r.id, 60)}
                    disabled={reminderBusy === r.id}
                  >
                    {t('app.candidate_card.reminders.snooze_60')}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )

  if (embedded) {
    return (
      <section className="w-full min-w-0">
        {remindersError && <p className="mb-2 text-xs text-rose-600">{remindersError}</p>}
        {fullContent}
      </section>
    )
  }

  return (
    <>
      <section className="card w-full p-4">
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex w-full items-center justify-between text-left"
        >
          <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
            {t('app.candidate_card.reminders.title')}
            {reminders.length > 0 && (
              <span className="inline-flex items-center rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                {reminders.length}
              </span>
            )}
          </h3>
        </button>
        <div className="mt-1 text-sm text-slate-600">
          {remindersError && <p className="text-xs text-rose-600">{remindersError}</p>}
          {!remindersError && (
            <p className="text-xs text-slate-500">
              {reminders.length === 0 && !remindersLoading
                ? t('app.candidate_card.reminders.subtitle')
                : reminders.length > 0
                  ? t('app.candidate_card.reminders.upcoming')
                  : t('common.loading', { defaultValue: 'Loading...' })}
            </p>
          )}
        </div>
        <div className="mt-3">
          <button
            type="button"
            className="btn-primary btn-sm"
            onClick={() => setOpen(true)}
          >
            {t('app.candidate_card.reminders.create')}
          </button>
        </div>
      </section>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="card max-h-[90vh] w-full max-w-lg overflow-auto p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-medium text-slate-900">
                {t('app.candidate_card.reminders.title')}
              </h4>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="btn-secondary btn-sm"
              >
                {t('common.actions.close', { defaultValue: 'Zamknij' })}
              </button>
            </div>
            {fullContent}
          </div>
        </div>
      )}
    </>
  )
}

export default memo(CandidateRemindersSection)
