import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listFunnels, type Funnel } from '../../api/funnels'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

interface FunnelSelectorProps {
  value: string | null | undefined
  onChange: (funnelId: string | null) => void
  disabled?: boolean
}

export default function FunnelSelector({ value, onChange, disabled = false }: FunnelSelectorProps) {
  const [funnels, setFunnels] = useState<Funnel[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const list = await listFunnels({ type: 'candidate' })
      setFunnels(list)
    } catch {
      setFunnels([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const selectedFunnel = funnels.find((f) => f.id === value)

  if (loading) {
    return <div className="text-sm text-slate-500">Загрузка воронок…</div>
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Воронка (этапы)</label>
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value || null)}
          disabled={disabled}
          className="input w-full max-w-md"
        >
          <option value="">— не выбрана —</option>
          {funnels.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
              {f.is_default ? ' ★' : ''}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-slate-500">
          Этапы берутся из справочника воронок.{' '}
          <Link to={CRM_APP_PATHS.settingsFunnels} className="text-brand-600 hover:underline">
            Редактировать воронки
          </Link>
        </p>
      </div>
      {selectedFunnel && selectedFunnel.stages && selectedFunnel.stages.length > 0 && (
        <div>
          <div className="text-sm font-medium text-slate-700 mb-2">Этапы выбранной воронки</div>
          <div className="flex flex-wrap gap-2">
            {selectedFunnel.stages.map((s) => (
              <span
                key={s.id}
                className="inline-flex rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700"
              >
                {s.label} <span className="text-slate-500 font-mono">({s.code})</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
