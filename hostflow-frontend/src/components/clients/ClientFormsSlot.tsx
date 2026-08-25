import { useEffect, useState } from 'react'
import { listFormsPlatformHandlers, type FormsPlatformHandler } from '../../api/formsPlatform'
import { useI18n } from '../../i18n'

/** D5 forms slot — Forms public handlers only. Not Builder / P3 Publish UI. */
export function ClientFormsSlot() {
  const { t } = useI18n()
  const [handlers, setHandlers] = useState<FormsPlatformHandler[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let mounted = true
    const run = async () => {
      setLoading(true)
      try {
        const rows = await listFormsPlatformHandlers()
        if (!mounted) return
        setHandlers(rows)
      } catch {
        if (mounted) setHandlers([])
      } finally {
        if (mounted) setLoading(false)
      }
    }
    void run()
    return () => {
      mounted = false
    }
  }, [])

  const sales = handlers.find((row) => (row.creates || []).includes('sales_inquiry'))

  return (
    <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm font-semibold text-slate-900">
        {t('app.entity_workspace.slot.forms', { defaultValue: 'Формы' })}
      </p>
      <p className="text-sm text-slate-600">
        {loading
          ? t('app.clients.forms.loading', { defaultValue: 'Загрузка форм…' })
          : sales
            ? t('app.clients.forms.bound', {
                defaultValue: 'Анкета клиента идёт через Forms Platform',
              })
            : t('app.clients.forms.empty', {
                defaultValue: 'Нет связанной анкеты Forms Platform',
              })}
      </p>
    </div>
  )
}
