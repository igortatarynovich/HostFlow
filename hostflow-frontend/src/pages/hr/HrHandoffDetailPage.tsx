import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { acceptHandoff } from '../../api/handoffs'
import {
  fetchHandoffHrReview,
  fetchHrHandoffInboxRow,
  type HrHandoffInboxItem,
} from '../../api/hrWorkspace'
import HrReviewPanelCard from '../../components/hr/HrReviewPanel'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import type { HrReviewPanel } from '../../api/workforce'

export default function HrHandoffDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useI18n()
  const { notify } = useToast()
  const [row, setRow] = useState<HrHandoffInboxItem | null>(null)
  const [hrReview, setHrReview] = useState<HrReviewPanel | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setErr(null)
    try {
      const inboxRow = await fetchHrHandoffInboxRow(id)
      setRow(inboxRow)
      if (inboxRow.handoff.status === 'accepted') {
        try {
          const panel = await fetchHandoffHrReview(id)
          setHrReview(panel)
        } catch {
          setHrReview(null)
        }
      } else {
        setHrReview(null)
      }
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: string } }; message?: string }
      setErr(ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'))
      setRow(null)
      setHrReview(null)
    } finally {
      setLoading(false)
    }
  }, [id, t])

  useEffect(() => {
    void load()
  }, [load])

  const handleAcceptPickup = async () => {
    if (!id) return
    setAccepting(true)
    try {
      await acceptHandoff(id)
      notify({
        variant: 'success',
        title: t('app.nav.hr.handoff.accept_pickup', { defaultValue: 'Take into HR review' }),
      })
      await load()
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: string } }; message?: string }
      notify({
        variant: 'error',
        title: ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'),
      })
    } finally {
      setAccepting(false)
    }
  }

  const isPickup = row?.operational_queue === 'awaiting_hr_pickup'
  const empId = row?.workforce_employee_id || hrReview?.employee_id || undefined

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Link to={CRM_APP_PATHS.hrInbox} className="text-sm font-medium text-brand-700 hover:text-brand-900">
          ← {t('app.nav.hr.handoff.back_inbox', { defaultValue: 'Back to inbox' })}
        </Link>
      </div>
      <h2 className="text-base font-semibold text-slate-900">
        {t('app.nav.hr.handoff.title', { defaultValue: 'Internal HR handoff' })}
        {row?.candidate_display_name ? ` · ${row.candidate_display_name}` : null}
      </h2>
      <p className="text-sm text-slate-600">
        {t('app.nav.hr.handoff.hint', {
          defaultValue:
            'Review transfer data, take the case into HR review, then approve for employment when ready.',
        })}
      </p>

      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>
      )}

      {row && !loading ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          <span className="font-semibold">{row.operational_queue.replace(/_/g, ' ')}</span>
          {row.hr_review_status ? <span className="ml-2">· {row.hr_review_status.replace(/_/g, ' ')}</span> : null}
        </div>
      ) : null}

      {isPickup && !loading ? (
        <div>
          <button type="button" className="btn-primary" disabled={accepting} onClick={() => void handleAcceptPickup()}>
            {t('app.nav.hr.handoff.accept_pickup', { defaultValue: 'Take into HR review' })}
          </button>
        </div>
      ) : null}

      {hrReview && !isPickup ? (
        <>
          <p className="text-sm text-slate-600">
            {t('app.nav.hr.handoff.accepted_notice', {
              defaultValue:
                'Case is in HR review. Complete the checklist below, then approve for employment when ready.',
            })}
          </p>
          <HrReviewPanelCard
            handoffId={id!}
            employeeId={empId}
            panel={hrReview}
            manage
            onUpdated={(next) => {
              setHrReview(next)
              void load()
            }}
          />
        </>
      ) : null}

      {empId ? (
        <Link className="text-sm font-medium text-brand-700 hover:underline" to={`${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(empId)}`}>
          {t('app.nav.hr.inbox.open_employee', { defaultValue: 'Employee profile' })}
        </Link>
      ) : null}
    </div>
  )
}
