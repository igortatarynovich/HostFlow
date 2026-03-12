import { useEffect, useState } from 'react'
import { Modal } from '../../../components/Modal'
import { useI18n } from '../../../i18n'
import { getAvailableClients, type AvailableClientOut } from '../../../api/handoffs'

interface BulkHandoffModalProps {
  open: boolean
  onClose: () => void
  clients: AvailableClientOut[]
  clientsLoading: boolean
  selectedClient: string
  onSelectedClientChange: (id: string) => void
  onApply: () => void
  loading: boolean
  canManage?: boolean
  count: number
}

export function BulkHandoffModal({
  open,
  onClose,
  clients,
  clientsLoading,
  selectedClient,
  onSelectedClientChange,
  onApply,
  loading,
  canManage = true,
  count,
}: BulkHandoffModalProps) {
  const { t } = useI18n()

  const companyClients = clients.filter((c) => c.client_company_id)

  useEffect(() => {
    if (open && companyClients.length > 0 && !selectedClient) {
      onSelectedClientChange(companyClients[0].client_company_id!)
    }
  }, [open, companyClients, selectedClient, onSelectedClientChange])

  return (
    <Modal
      open={canManage && open}
      onClose={() => {
        if (!loading) onClose()
      }}
      title={t('app.candidates.modals.handoff.title', { defaultValue: 'Przekaż do klienta (zbiorczo)' })}
    >
      <div className="space-y-3">
        {(loading || clientsLoading) && (
          <div className="flex items-center gap-2 text-sm text-brand-600 bg-brand-50 p-2 rounded border border-brand-200">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-600"></div>
            <span>
              {loading
                ? t('common.loading') || 'Zapisywanie...'
                : t('app.candidates.messages.bulk_handoff_loading', { defaultValue: 'Ładowanie klientów...' })}
            </span>
          </div>
        )}
        <p className="text-sm text-slate-600">
          {t('app.candidates.modals.handoff.hint', {
            values: { count },
            defaultValue: `Przekaż ${count} wybranych kandydatów do klienta.`,
          })}
        </p>
        <div>
          <div className="label">{t('app.candidates.modals.handoff.client_label', { defaultValue: 'Klient' })}</div>
          <select
            className="input"
            value={selectedClient}
            onChange={(e) => onSelectedClientChange(e.target.value)}
            disabled={loading || clientsLoading}
          >
            <option value="">{t('app.candidates.select.placeholder')}</option>
            {companyClients.map((c) => (
              <option key={c.link_id} value={c.client_company_id!}>
                {c.client_name}
              </option>
            ))}
          </select>
        </div>
        {companyClients.length === 0 && !clientsLoading && (
          <p className="text-sm text-amber-600">
            {t('app.candidates.modals.handoff.no_clients', {
              defaultValue: 'Brak klientów z włączoną przekazywaniem.',
            })}
          </p>
        )}
        <div className="flex gap-2">
          <button
            className="btn-primary"
            onClick={onApply}
            disabled={loading || clientsLoading || !selectedClient || companyClients.length === 0}
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {t('common.loading') || 'Zapisywanie...'}
              </>
            ) : (
              t('app.candidates.modals.handoff.apply', { defaultValue: 'Przekaż' })
            )}
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            {t('common.actions.cancel')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
