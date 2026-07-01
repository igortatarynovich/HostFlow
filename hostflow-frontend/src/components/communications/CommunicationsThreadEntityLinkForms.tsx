import { useEffect, useState } from 'react'
import clsx from 'clsx'
import { Link } from 'react-router-dom'
import { searchCandidates } from '../../api/candidates'
import { getServiceOrder, listServiceOrders } from '../../api/additionalServices'
import { patchCommunicationThread, type CommunicationThread } from '../../api/communications'
import { api, listCompanies } from '../../api/client'
import type { AdditionalServiceOrder, Candidate } from '../../api/types'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { serviceOrderWorkspacePath } from '../../modules/services/utils'
import { isCommunicationThreadUnlinked, uosLinkedServiceOrderId } from '../../utils/communicationThreadUnlinked'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'

type CompanyRow = { id: string; legal_name?: string | null; name?: string | null }

function normalizeCompanyRows(data: unknown): CompanyRow[] {
  if (Array.isArray(data)) return data as CompanyRow[]
  const items = (data as { items?: unknown })?.items
  return Array.isArray(items) ? (items as CompanyRow[]) : []
}

async function resolveCandidateDisplayName(candidateId: string, selected: Candidate | null): Promise<string> {
  if (selected && String(selected.id) === String(candidateId)) {
    const n = [String(selected.first_name || '').trim(), String(selected.last_name || '').trim()]
      .filter(Boolean)
      .join(' ')
      .trim()
    if (n) return n
  }
  try {
    const { data } = await api.get(`/candidates/${candidateId}`)
    const item = data?.item || data
    const first = String(item?.first_name || '').trim()
    const last = String(item?.last_name || '').trim()
    const full = [first, last].filter(Boolean).join(' ').trim()
    if (full) return full
    return String(item?.short_id || candidateId)
  } catch {
    return ''
  }
}

type Props = {
  thread: CommunicationThread
  /** After successful PATCH that changes links or meta */
  onAfterPatch: () => void | Promise<void>
  compact?: boolean
  /** Tighter layout for slide-down header panel (Messages). */
  dense?: boolean
}

export default function CommunicationsThreadEntityLinkForms({ thread, onAfterPatch, compact, dense }: Props) {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const unlinked = isCommunicationThreadUnlinked(thread)
  const cid = String(thread.linked_candidate_id || '').trim()
  const compId = String(thread.linked_company_id || '').trim()
  const linkedOrderId = uosLinkedServiceOrderId(thread.thread_meta)

  const [linkBusy, setLinkBusy] = useState(false)
  const [linkError, setLinkError] = useState<FriendlyErrorInfo | null>(null)
  const [linkOk, setLinkOk] = useState<string | null>(null)

  const [candidateQuery, setCandidateQuery] = useState('')
  const [candidateResults, setCandidateResults] = useState<Candidate[]>([])
  const [candidatePickId, setCandidatePickId] = useState('')
  const [candidateSearching, setCandidateSearching] = useState(false)

  const [companyQuery, setCompanyQuery] = useState('')
  const [companyResults, setCompanyResults] = useState<CompanyRow[]>([])
  const [companyPickId, setCompanyPickId] = useState('')
  const [companySearching, setCompanySearching] = useState(false)

  const [orderOptions, setOrderOptions] = useState<AdditionalServiceOrder[]>([])
  const [orderPickId, setOrderPickId] = useState('')
  const [orderIdManual, setOrderIdManual] = useState('')

  useEffect(() => {
    setLinkError(null)
    setLinkOk(null)
    setCandidateQuery('')
    setCandidateResults([])
    setCandidatePickId('')
    setCompanyQuery('')
    setCompanyResults([])
    setCompanyPickId('')
    setOrderIdManual('')
  }, [thread.id])

  useEffect(() => {
    const linked = uosLinkedServiceOrderId(thread.thread_meta)
    setOrderPickId(linked)
    if (!cid && !compId) {
      setOrderOptions([])
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const rows = await listServiceOrders({
          ...(cid ? { candidateId: cid } : {}),
          ...(compId ? { companyId: compId } : {}),
        })
        if (cancelled) return
        const list = Array.isArray(rows) ? rows.slice(0, 40) : []
        setOrderOptions(list)
      } catch {
        if (!cancelled) setOrderOptions([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [thread.id, thread.thread_meta, cid, compId])

  const runCandidateSearch = async () => {
    const q = candidateQuery.trim()
    if (q.length < 2) {
      setCandidateResults([])
      setCandidatePickId('')
      return
    }
    setCandidateSearching(true)
    setLinkError(null)
    try {
      const list = await searchCandidates({ q, limit: 15 })
      setCandidateResults(list)
      const firstId = list[0]?.id ? String(list[0].id) : ''
      setCandidatePickId((prev) => (prev && list.some((x) => String(x.id) === prev) ? prev : firstId))
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.link_search_candidate_failed', { defaultValue: 'Candidate search failed.' }),
        )
      ) {
        const fe = getFriendlyErrorInfo(
          err,
          t('app.communications_inbox_center.link_search_candidate_failed', { defaultValue: 'Candidate search failed.' }),
          t,
        )
        setLinkError(fe)
      }
    } finally {
      setCandidateSearching(false)
    }
  }

  const bindCandidate = async (candidateId: string | null) => {
    setLinkBusy(true)
    setLinkError(null)
    setLinkOk(null)
    try {
      const selectedCandidate =
        candidateId && candidateResults.length ? candidateResults.find((c) => String(c.id) === String(candidateId)) : null
      const linkedName = candidateId ? await resolveCandidateDisplayName(candidateId, selectedCandidate || null) : ''
      const nextMeta = {
        ...(thread.thread_meta || {}),
        linked_candidate_name: candidateId ? linkedName || undefined : null,
      }
      await patchCommunicationThread(thread.id, {
        linked_candidate_id: candidateId,
        thread_meta: nextMeta,
      })
      setCandidateResults([])
      setCandidateQuery('')
      setCandidatePickId('')
      setLinkOk(
        candidateId
          ? t('app.communications_inbox_center.link_ok_candidate', { defaultValue: 'Кандидат привязан.' })
          : t('app.communications_inbox_center.link_ok_candidate_cleared', { defaultValue: 'Привязка кандидата снята.' }),
      )
      await onAfterPatch()
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.link_error_candidate', { defaultValue: 'Could not update candidate link.' }),
        )
      ) {
        const fe = getFriendlyErrorInfo(
          err,
          t('app.communications_inbox_center.link_error_candidate', { defaultValue: 'Could not update candidate link.' }),
          t,
        )
        setLinkError(fe)
      }
    } finally {
      setLinkBusy(false)
    }
  }

  const runCompanySearch = async () => {
    const q = companyQuery.trim()
    if (q.length < 2) {
      setCompanyResults([])
      setCompanyPickId('')
      return
    }
    setCompanySearching(true)
    setLinkError(null)
    try {
      const rows = await listCompanies({ limit: 25, search: q })
      const list = normalizeCompanyRows(rows)
      setCompanyResults(list)
      const firstId = list[0]?.id ? String(list[0].id) : ''
      setCompanyPickId((prev) => (prev && list.some((x) => String(x.id) === prev) ? prev : firstId))
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.link_search_company_failed', { defaultValue: 'Client search failed.' }),
        )
      ) {
        const fe = getFriendlyErrorInfo(
          err,
          t('app.communications_inbox_center.link_search_company_failed', { defaultValue: 'Client search failed.' }),
          t,
        )
        setLinkError(fe)
      }
    } finally {
      setCompanySearching(false)
    }
  }

  const bindCompany = async (companyId: string | null) => {
    setLinkBusy(true)
    setLinkError(null)
    setLinkOk(null)
    try {
      const selectedCo = companyId && companyResults.length ? companyResults.find((c) => String(c.id) === String(companyId)) : null
      const linkedName = selectedCo ? String(selectedCo.legal_name || selectedCo.name || '').trim() : ''
      const nextMeta = {
        ...(thread.thread_meta || {}),
        linked_company_name: companyId ? linkedName || undefined : null,
      }
      await patchCommunicationThread(thread.id, {
        linked_company_id: companyId,
        thread_meta: nextMeta,
      })
      setCompanyResults([])
      setCompanyQuery('')
      setCompanyPickId('')
      setLinkOk(
        companyId
          ? t('app.communications_inbox_center.link_ok_client', { defaultValue: 'Клиент привязан.' })
          : t('app.communications_inbox_center.link_ok_client_cleared', { defaultValue: 'Привязка клиента снята.' }),
      )
      await onAfterPatch()
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.link_error_company', { defaultValue: 'Could not update client link.' }),
        )
      ) {
        const fe = getFriendlyErrorInfo(
          err,
          t('app.communications_inbox_center.link_error_company', { defaultValue: 'Could not update client link.' }),
          t,
        )
        setLinkError(fe)
      }
    } finally {
      setLinkBusy(false)
    }
  }

  const persistLinkedServiceOrder = async (orderId: string | null) => {
    setLinkBusy(true)
    setLinkError(null)
    setLinkOk(null)
    try {
      const meta = { ...(thread.thread_meta || {}) }
      const prevUos =
        typeof meta.uos === 'object' && meta.uos && !Array.isArray(meta.uos)
          ? { ...(meta.uos as Record<string, unknown>) }
          : {}
      if (orderId) {
        const fromList = orderOptions.find((o) => String(o.id) === String(orderId))
        prevUos.linked_service_order_id = orderId
        prevUos.linked_service_order_label = fromList
          ? `${String(fromList.status || 'order')} · ${String(fromList.id).slice(0, 8)}…`
          : `${orderId.slice(0, 8)}…`
      } else {
        delete prevUos.linked_service_order_id
        delete prevUos.linked_service_order_label
      }
      meta.uos = prevUos
      await patchCommunicationThread(thread.id, { thread_meta: meta })
      setOrderPickId(orderId || '')
      setLinkOk(
        orderId
          ? t('app.communications_inbox_center.link_ok_order', { defaultValue: 'Заказ привязан.' })
          : t('app.communications_inbox_center.link_ok_order_cleared', { defaultValue: 'Привязка заказа снята.' }),
      )
      await onAfterPatch()
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.link_error_order', { defaultValue: 'Could not update service order link.' }),
        )
      ) {
        const fe = getFriendlyErrorInfo(
          err,
          t('app.communications_inbox_center.link_error_order', { defaultValue: 'Could not update service order link.' }),
          t,
        )
        setLinkError(fe)
      }
    } finally {
      setLinkBusy(false)
    }
  }

  const linkServiceOrderByManualId = async () => {
    const id = orderIdManual.trim()
    if (!id) return
    setLinkBusy(true)
    setLinkError(null)
    setLinkOk(null)
    try {
      await getServiceOrder(id)
      const meta = { ...(thread.thread_meta || {}) }
      const prevUos =
        typeof meta.uos === 'object' && meta.uos && !Array.isArray(meta.uos)
          ? { ...(meta.uos as Record<string, unknown>) }
          : {}
      prevUos.linked_service_order_id = id
      prevUos.linked_service_order_label = `${id.slice(0, 8)}…`
      meta.uos = prevUos
      await patchCommunicationThread(thread.id, { thread_meta: meta })
      setOrderIdManual('')
      setLinkOk(t('app.communications_inbox_center.link_ok_order', { defaultValue: 'Заказ привязан.' }))
      await onAfterPatch()
    } catch (err: unknown) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.communications_inbox_center.link_order_not_found', { defaultValue: 'Order not found or access denied.' }),
        )
      ) {
        const fe = getFriendlyErrorInfo(
          err,
          t('app.communications_inbox_center.link_order_not_found', { defaultValue: 'Order not found or access denied.' }),
          t,
        )
        setLinkError(fe)
      }
    } finally {
      setLinkBusy(false)
    }
  }

  return (
    <div
      className={clsx(
        'rounded-lg border border-slate-200 bg-slate-50/80',
        dense ? 'p-2 text-xs' : 'p-3',
      )}
    >
      {!dense && (
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.communications_inbox_center.linked_entities', { defaultValue: 'Linked entities' })}
        </div>
      )}
      {!compact && !dense && (
        <p className="mt-1 text-[11px] text-slate-500">
          {t('app.communications_messages.header.link_forms_hint', {
            defaultValue: 'Поиск и привязка кандидата, клиента и заказа — здесь, в чате.',
          })}
        </p>
      )}
      {unlinked && !dense && (
        <div className="mt-2 rounded-md border border-amber-200/80 bg-amber-50/90 px-2.5 py-1.5 text-[11px] text-amber-950">
          {t('app.communications_inbox_center.unlinked_hint_short', { defaultValue: 'Not linked — use search below.' })}
        </div>
      )}
      {linkError ? (
        <p className={clsx('text-rose-600', dense ? 'mt-1 text-[11px]' : 'mt-2 text-xs')}>
          {linkError.title}
          {linkError.detail ? ` — ${linkError.detail}` : ''}
        </p>
      ) : null}
      {linkOk && !linkError && (
        <p className={clsx('text-emerald-700', dense ? 'mt-1 text-[11px]' : 'mt-2 text-xs')}>{linkOk}</p>
      )}

      <ul className={clsx('space-y-1', dense ? 'mt-1 text-xs' : 'mt-2 space-y-1.5 text-sm')}>
        {cid ? (
          <li className="flex flex-wrap items-center gap-2">
            <Link
              className="font-medium text-brand-700 hover:text-brand-900 hover:underline"
              to={`${CRM_APP_PATHS.candidates}/${cid}`}
            >
              {t('app.communications_inbox_center.open_candidate', { defaultValue: 'Open candidate' })}
            </Link>
            <button
              type="button"
              className="text-xs font-medium text-rose-700 hover:underline disabled:opacity-50"
              disabled={linkBusy}
              onClick={() => void bindCandidate(null)}
            >
              {t('app.communications_messages.candidate.unlink', { defaultValue: 'Unlink' })}
            </button>
          </li>
        ) : (
          <li className="text-slate-500">{t('app.communications_inbox_center.no_candidate', { defaultValue: 'No candidate linked' })}</li>
        )}
        {compId ? (
          <li className="flex flex-wrap items-center gap-2">
            <Link
              className="font-medium text-brand-700 hover:text-brand-900 hover:underline"
              to={`${CRM_APP_PATHS.agencyClients}/${compId}`}
            >
              {t('app.communications_inbox_center.open_client', { defaultValue: 'Open client' })}
            </Link>
            <button
              type="button"
              className="text-xs font-medium text-rose-700 hover:underline disabled:opacity-50"
              disabled={linkBusy}
              onClick={() => void bindCompany(null)}
            >
              {t('app.communications_messages.uos.unlink_client', { defaultValue: 'Unlink' })}
            </button>
          </li>
        ) : (
          <li className="text-slate-500">{t('app.communications_inbox_center.no_client', { defaultValue: 'No client linked' })}</li>
        )}
      </ul>

      <div className={clsx('border-t border-slate-200', dense ? 'mt-2 pt-2' : 'mt-3 pt-3')}>
        <div className={clsx('font-semibold uppercase tracking-wide text-slate-500', dense ? 'text-[10px]' : 'text-xs')}>
          {t('app.communications_messages.candidate.label', { defaultValue: 'Candidate' })}
        </div>
        <div className={clsx('flex flex-wrap gap-2', dense ? 'mt-1' : 'mt-2')}>
          <input
            value={candidateQuery}
            onChange={(e) => setCandidateQuery(e.target.value)}
            placeholder={t('app.communications_messages.candidate.search_placeholder', {
              defaultValue: 'Find by name / email / phone / short ID',
            })}
            className="min-w-[140px] flex-1 input text-sm"
            disabled={linkBusy}
          />
          <button
            type="button"
            className="btn-secondary btn-sm shrink-0 disabled:opacity-50"
            disabled={linkBusy || candidateSearching || candidateQuery.trim().length < 2}
            onClick={() => void runCandidateSearch()}
          >
            {candidateSearching ? t('common.loading') : t('app.communications_messages.actions.search', { defaultValue: 'Search' })}
          </button>
        </div>
        {candidateResults.length > 0 && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <select
              value={candidatePickId}
              onChange={(e) => setCandidatePickId(e.target.value)}
              className="min-w-0 flex-1 input text-sm"
              disabled={linkBusy}
            >
              {candidateResults.map((c) => (
                <option key={c.id} value={c.id}>
                  {[String(c.first_name || '').trim(), String(c.last_name || '').trim()].filter(Boolean).join(' ') || String(c.id)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-primary btn-sm shrink-0 disabled:opacity-50"
              disabled={linkBusy || !candidatePickId}
              onClick={() => void bindCandidate(candidatePickId || null)}
            >
              {t('app.communications_messages.candidate.link', { defaultValue: 'Link candidate' })}
            </button>
          </div>
        )}
      </div>

      <div className={clsx('border-t border-slate-200', dense ? 'mt-2 pt-2' : 'mt-3 pt-3')}>
        <div className={clsx('font-semibold uppercase tracking-wide text-slate-500', dense ? 'text-[10px]' : 'text-xs')}>
          {t('app.communications_messages.uos.client', { defaultValue: 'Client (company)' })}
        </div>
        <div className={clsx('flex flex-wrap gap-2', dense ? 'mt-1' : 'mt-2')}>
          <input
            value={companyQuery}
            onChange={(e) => setCompanyQuery(e.target.value)}
            placeholder={t('app.communications_messages.uos.client_search_placeholder', { defaultValue: 'Company name…' })}
            className="min-w-[140px] flex-1 input text-sm"
            disabled={linkBusy}
          />
          <button
            type="button"
            className="btn-secondary btn-sm shrink-0 disabled:opacity-50"
            disabled={linkBusy || companySearching || companyQuery.trim().length < 2}
            onClick={() => void runCompanySearch()}
          >
            {companySearching ? t('common.loading') : t('app.communications_messages.actions.search', { defaultValue: 'Search' })}
          </button>
        </div>
        {companyResults.length > 0 && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <select
              value={companyPickId}
              onChange={(e) => setCompanyPickId(e.target.value)}
              className="min-w-0 flex-1 input text-sm"
              disabled={linkBusy}
            >
              {companyResults.map((c) => (
                <option key={c.id} value={c.id}>
                  {String(c.legal_name || c.name || c.id)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-primary btn-sm shrink-0 disabled:opacity-50"
              disabled={linkBusy || !companyPickId}
              onClick={() => void bindCompany(companyPickId || null)}
            >
              {t('app.communications_messages.uos.link_client', { defaultValue: 'Link client' })}
            </button>
          </div>
        )}
      </div>

      <div className={clsx('border-t border-slate-200', dense ? 'mt-2 pt-2' : 'mt-3 pt-3')}>
        <div className={clsx('font-semibold uppercase tracking-wide text-slate-500', dense ? 'text-[10px]' : 'text-xs')}>
          {t('app.communications_messages.uos.order', { defaultValue: 'Service order' })}
        </div>
        {linkedOrderId ? (
          <div className="mt-2 rounded-md border border-slate-100 bg-white p-2 text-xs">
            <div className="font-medium text-slate-800">
              {String((thread.thread_meta?.uos as Record<string, unknown> | undefined)?.linked_service_order_label || '').trim() ||
                linkedOrderId}
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Link className="font-medium text-brand-700 hover:underline" to={serviceOrderWorkspacePath(String(linkedOrderId))}>
                {t('app.communications_messages.uos.open_order', { defaultValue: 'Open order' })}
              </Link>
              <button
                type="button"
                className="font-medium text-rose-700 hover:underline disabled:opacity-50"
                disabled={linkBusy}
                onClick={() => void persistLinkedServiceOrder(null)}
              >
                {t('app.communications_messages.uos.unlink_order', { defaultValue: 'Unlink' })}
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-2 space-y-2">
            {!cid && !compId ? (
              <p className="text-xs text-slate-500">
                {compact
                  ? t('app.communications_messages.uos.order_need_context_short', {
                      defaultValue: 'Link candidate/client or paste order ID.',
                    })
                  : t('app.communications_messages.uos.order_need_context', {
                      defaultValue: 'Link a candidate or client to load recent orders, or paste order ID below.',
                    })}
              </p>
            ) : orderOptions.length === 0 ? (
              <p className="text-xs text-slate-500">
                {t('app.communications_messages.uos.order_empty', { defaultValue: 'No orders found for this context.' })}
              </p>
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={orderPickId}
                  onChange={(e) => setOrderPickId(e.target.value)}
                  className="min-w-0 flex-1 input text-sm"
                  disabled={linkBusy}
                >
                  <option value="">{t('app.communications_messages.uos.order_select', { defaultValue: 'Select order…' })}</option>
                  {orderOptions.map((o) => (
                    <option key={o.id} value={o.id}>
                      {String(o.status || 'order')} · {String(o.id).slice(0, 8)}…
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-primary btn-sm shrink-0 disabled:opacity-50"
                  disabled={linkBusy || !orderPickId}
                  onClick={() => void persistLinkedServiceOrder(orderPickId || null)}
                >
                  {t('app.communications_messages.uos.link_order', { defaultValue: 'Link' })}
                </button>
              </div>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={orderIdManual}
                onChange={(e) => setOrderIdManual(e.target.value)}
                placeholder={t('app.communications_messages.uos.order_id_placeholder', { defaultValue: 'Order UUID' })}
                className="min-w-[140px] flex-1 input font-mono text-xs"
                disabled={linkBusy}
              />
              <button
                type="button"
                className="btn-secondary btn-sm shrink-0 disabled:opacity-50"
                disabled={linkBusy || !orderIdManual.trim()}
                onClick={() => void linkServiceOrderByManualId()}
              >
                {t('app.communications_messages.uos.link_order_by_id', { defaultValue: 'Link ID' })}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
