import { memo, useCallback, useEffect, useState } from 'react'
import { IconCheck } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import type { UUID } from '../../api/types'
import {
  getAvailableClients,
  getHandoffStatus,
  createHandoff,
  acceptHandoff,
  rejectHandoff,
  returnHandoff,
  type HandoffStatusResponse,
  type AvailableClientOut,
} from '../../api/handoffs'
import { formatDateTime } from '../../utils/dateFormat'
import { useToast } from '../Toast'

interface CandidateHandoffSectionProps {
  candidateId: UUID
  companyId?: string | null
  onHandoffCreated?: () => void
  embedded?: boolean
}

function CandidateHandoffSection({
  candidateId,
  companyId,
  onHandoffCreated,
  embedded = false,
}: CandidateHandoffSectionProps) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [status, setStatus] = useState<HandoffStatusResponse | null>(null)
  const [clients, setClients] = useState<AvailableClientOut[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [selectedClient, setSelectedClient] = useState<AvailableClientOut | null>(null)
  const [decisionForm, setDecisionForm] = useState<null | 'return' | 'reject'>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [returnReason, setReturnReason] = useState('')

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [st, cl] = await Promise.all([
        getHandoffStatus(candidateId, companyId as UUID | undefined),
        getAvailableClients(),
      ])
      setStatus(st)
      setClients(cl)
    } catch {
      setStatus(null)
      setClients([])
    } finally {
      setLoading(false)
    }
  }, [candidateId, companyId])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  const handleSubmit = async () => {
    if (!selectedClient) return
    setSubmitting(true)
    try {
      const payload = selectedClient.client_company_id
        ? { client_company_id: selectedClient.client_company_id }
        : selectedClient.client_tenant_id
          ? { client_tenant_id: selectedClient.client_tenant_id }
          : null
      if (!payload) return
      await createHandoff(candidateId, payload)
      setSelectedClient(null)
      await fetchData()
      onHandoffCreated?.()
      notify({
        title: t('app.candidate_card.handoff.created', {
          defaultValue: 'Przekazano do klienta',
        }),
        variant: 'success',
      })
    } catch (e: any) {
      notify({
        title: e?.response?.data?.detail ?? 'Error',
        variant: 'error',
      })
    } finally {
      setSubmitting(false)
    }
  }

  if (loading || !status) {
    return (
      <section className={embedded ? 'w-full p-0' : 'card w-full p-4'}>
        <h3 className="text-sm font-medium text-slate-700">
          {t('app.candidate_card.handoff.title', { defaultValue: 'Przekazanie' })}
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          {loading ? t('common.loading', { defaultValue: 'Loading...' }) : '—'}
        </p>
      </section>
    )
  }

  const canHandoff = !status.pending && !status.accepted && clients.length > 0

  return (
    <section className={embedded ? 'w-full p-0' : 'card w-full p-4'}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
          {t('app.candidate_card.handoff.title', { defaultValue: 'Przekazanie' })}
          {status.pending && (
            <span className="inline-flex items-center rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              {t('app.handoff.status.pending')}
            </span>
          )}
          {status.accepted && (
            <span className="inline-flex items-center gap-1 rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
              <IconCheck size={12} />
              {t('app.handoff.status.accepted')}
            </span>
          )}
        </h3>
      </div>
      <div className="mt-2 text-sm text-slate-600">
        {canHandoff && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <label className="label">{t('app.candidate_card.handoff.client', { defaultValue: 'Klient' })}</label>
            <select
              value={selectedClient?.link_id ?? ''}
              onChange={(e) => {
                const c = clients.find((x) => x.link_id === e.target.value)
                setSelectedClient(c ?? null)
              }}
              className="input mt-1"
            >
              <option value="">—</option>
              {clients.some((c) => c.client_company_id) && (
                <optgroup label={t('app.handoff.client_type_firm', { defaultValue: 'Firmy' })}>
                  {clients.filter((c) => c.client_company_id).map((c) => (
                    <option key={c.link_id} value={c.link_id}>
                      {c.client_name}
                    </option>
                  ))}
                </optgroup>
              )}
              {clients.some((c) => c.client_tenant_id) && (
                <optgroup label={t('app.handoff.client_type_org', { defaultValue: 'Organizacje (portal klienta)' })}>
                  {clients.filter((c) => c.client_tenant_id).map((c) => (
                    <option key={c.link_id} value={c.link_id}>
                      {c.client_name}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
            <p className="mt-1.5 text-xs text-slate-500">
              {t('app.handoff.client_hint', { defaultValue: 'Organizacje — klienci z własnym portalem. Firmy — w ramach Twojego workspace.' })}
            </p>
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting || !selectedClient}
                className="btn-primary btn-sm"
              >
                {submitting
                  ? t('common.saving', { defaultValue: 'Zapisywanie...' })
                  : t('app.candidate_card.handoff.transfer_btn', { defaultValue: 'Przekaż do klienta' })}
              </button>
            </div>
          </div>
        )}
        {status.pending && (
          <div>
            <p>
              {t('app.candidate_card.handoff.pending', {
                defaultValue: 'Oczekuje na decyzję klienta',
              })}{' '}
              ({formatDateTime(status.pending.requested_at)})
            </p>
            {status.client_owns && (
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={async () => {
                    setSubmitting(true)
                    try {
                      await acceptHandoff(status.pending!.id)
                      await fetchData()
                      onHandoffCreated?.()
                      notify({
                        title: t('app.handoff.accepted', { defaultValue: 'Przyjęto' }),
                        variant: 'success',
                      })
                    } catch (e: any) {
                      notify({
                        title: e?.response?.data?.detail ?? 'Error',
                        variant: 'error',
                      })
                    } finally {
                      setSubmitting(false)
                    }
                  }}
                  disabled={submitting}
                  className="btn-primary btn-sm"
                >
                  {t('app.handoff.accept_btn', { defaultValue: 'Przyjmij' })}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDecisionForm('return')
                    setRejectReason('')
                  }}
                  disabled={submitting}
                  className="btn-secondary btn-sm"
                >
                  {t('app.handoff.return_btn', { defaultValue: 'Zwróć' })}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDecisionForm('reject')
                    setReturnReason('')
                  }}
                  disabled={submitting}
                  className="btn-danger btn-sm"
                >
                  {t('app.handoff.reject_btn', { defaultValue: 'Odrzuć' })}
                </button>
              </div>
            )}
            {status.client_owns && decisionForm === 'return' && (
              <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <label className="label">
                  {t('app.handoff.return_reason', { defaultValue: 'Powód (wymagane)' })}
                </label>
                <textarea
                  value={returnReason}
                  onChange={(e) => setReturnReason(e.target.value)}
                  rows={3}
                  className="input mt-1"
                  placeholder={t('app.handoff.return_reason_placeholder', { defaultValue: 'Np. potrzebujemy dodatkowych dokumentów...' })}
                />
                <div className="mt-3 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setDecisionForm(null)
                      setReturnReason('')
                    }}
                    disabled={submitting}
                    className="btn-secondary btn-sm"
                  >
                    {t('common.cancel', { defaultValue: 'Anuluj' })}
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!returnReason.trim()) return
                      setSubmitting(true)
                      try {
                        await returnHandoff(status.pending!.id, returnReason.trim())
                        setDecisionForm(null)
                        setReturnReason('')
                        await fetchData()
                        onHandoffCreated?.()
                        notify({
                          title: t('app.handoff.returned', { defaultValue: 'Zwrócono do agencji' }),
                          variant: 'success',
                        })
                      } catch (e: any) {
                        notify({
                          title: e?.response?.data?.detail ?? 'Error',
                          variant: 'error',
                        })
                      } finally {
                        setSubmitting(false)
                      }
                    }}
                    disabled={submitting || !returnReason.trim()}
                    className="btn-secondary btn-sm"
                  >
                    {t('app.handoff.return_btn', { defaultValue: 'Zwróć' })}
                  </button>
                </div>
              </div>
            )}
            {status.client_owns && decisionForm === 'reject' && (
              <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50/40 p-3">
                <label className="label">
                  {t('app.handoff.rejection_reason', { defaultValue: 'Powód (wymagane)' })}
                </label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  rows={3}
                  className="input mt-1"
                />
                <div className="mt-3 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setDecisionForm(null)
                      setRejectReason('')
                    }}
                    disabled={submitting}
                    className="btn-secondary btn-sm"
                  >
                    {t('common.cancel', { defaultValue: 'Anuluj' })}
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!rejectReason.trim()) return
                      setSubmitting(true)
                      try {
                        await rejectHandoff(status.pending!.id, rejectReason.trim())
                        setDecisionForm(null)
                        setRejectReason('')
                        await fetchData()
                        onHandoffCreated?.()
                        notify({
                          title: t('app.handoff.rejected', { defaultValue: 'Odrzucono' }),
                          variant: 'success',
                        })
                      } catch (e: any) {
                        notify({
                          title: e?.response?.data?.detail ?? 'Error',
                          variant: 'error',
                        })
                      } finally {
                        setSubmitting(false)
                      }
                    }}
                    disabled={submitting || !rejectReason.trim()}
                    className="btn-danger btn-sm"
                  >
                    {t('app.handoff.reject_btn', { defaultValue: 'Odrzuć' })}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
        {status.accepted && (
          <div>
            <p>
              {t('app.candidate_card.handoff.accepted', {
                defaultValue: 'Przekazano klientowi',
              })}{' '}
              ({formatDateTime(status.accepted.reviewed_at)})
            </p>
            {(status.accepted.assigned_to_user_name || status.accepted.requested_by_user_name) && (
              <p className="text-xs text-slate-500">
                {t('app.candidate_card.handoff.processor', {
                  defaultValue: 'Przekazał',
                })}{' '}
                {status.accepted.assigned_to_user_name ?? status.accepted.requested_by_user_name}
              </p>
            )}
          </div>
        )}
        {!status.pending && !status.accepted && clients.length === 0 && (
          <p className="text-slate-500">
            {t('app.candidate_card.handoff.no_clients', {
              defaultValue: 'Brak klientów z włączoną przekazywaniem',
            })}
          </p>
        )}
      </div>

    </section>
  )
}

export default memo(CandidateHandoffSection)
