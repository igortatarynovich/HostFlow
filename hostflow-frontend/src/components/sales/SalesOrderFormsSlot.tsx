import { useEffect, useState } from 'react'
import { listFormsPlatformHandlers, type FormsPlatformHandler } from '../../api/formsPlatform'
import { useI18n } from '../../i18n'

/** D6 forms slot — Forms public handlers only. Not Builder / P3 Publish UI. */
export function SalesOrderFormsSlot() {
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
          ? t('app.sales_orders.forms.loading', { defaultValue: 'Загрузка форм…' })
          : sales
            ? t('app.sales_orders.forms.bound', {
                defaultValue: 'Анкета заказа идёт через Forms Platform',
              })
            : t('app.sales_orders.forms.empty', {
                defaultValue: 'Нет связанной анкеты Forms Platform',
              })}
      </p>
    </div>
  )
}
