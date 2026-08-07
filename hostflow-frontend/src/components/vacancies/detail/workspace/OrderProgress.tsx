import { useI18n } from '../../../../i18n'

type Props = {
  quantityNeeded: number
  hired: number
  orderLineTitle?: string | null
}

export function OrderProgress({ quantityNeeded, hired, orderLineTitle }: Props) {
  const { t } = useI18n()

  const progress = quantityNeeded > 0 ? Math.min(100, Math.round((hired / quantityNeeded) * 100)) : 0
  const remaining = Math.max(0, quantityNeeded - hired)

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-700">
          {t('app.vacancies.workspace.order_progress.title', { defaultValue: 'Прогресс заказа' })}
        </h3>
        <span className="text-xs text-slate-500">
          {orderLineTitle ? orderLineTitle : t('app.vacancies.workspace.order_progress.line_linked', { defaultValue: 'Order Line' })}
        </span>
      </div>

      <div className="mb-2 h-3 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-blue-500 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">
          {t('app.vacancies.workspace.order_progress.filled', {
            defaultValue: 'Выполнено: {hired} / {total}',
            values: { hired, total: quantityNeeded },
          })}
        </span>
        <span className="font-medium text-slate-800">{progress}%</span>
      </div>

      {remaining > 0 && (
        <p className="mt-2 text-xs text-slate-500">
          {t('app.vacancies.workspace.order_progress.remaining', {
            defaultValue: 'Осталось: {remaining} позиций',
            values: { remaining },
          })}
        </p>
      )}

      <p className="mt-2 text-xs text-amber-600">
        {t('app.vacancies.workspace.order_progress.note', {
          defaultValue: 'Прогресс на основе нанятых кандидатов вакансии (до появления Order Fulfillment API)',
        })}
      </p>
    </div>
  )
}
