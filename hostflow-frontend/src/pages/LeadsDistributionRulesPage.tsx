import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconGripVertical } from '@tabler/icons-react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { getLeadDistribution, patchLeadDistribution, type LeadDistributionOut } from '../api/leadsDistribution'
import { useI18n } from '../i18n'
import { ACTIVATION_PATHS } from '../app/activationRoutes'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

const CRITERIA_IDS = ['working_hours', 'workload', 'language', 'experience'] as const
const ROUTE_LANGS = ['pl', 'en', 'de'] as const

function SortableCriterionRow({
  id,
  index,
  label,
  canEdit,
  dragAria,
}: {
  id: string
  index: number
  label: string
  canEdit: boolean
  dragAria: string
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
    disabled: !canEdit,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <li
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50 px-2 py-2 text-sm ${
        isDragging ? 'z-10 opacity-80 shadow-md ring-2 ring-brand-200' : ''
      }`}
    >
      <span className="w-6 shrink-0 text-center font-mono text-xs text-slate-500">{index + 1}</span>
      <button
        type="button"
        className="-ml-1 shrink-0 touch-none rounded p-1 text-slate-400 hover:bg-white hover:text-slate-600 disabled:cursor-not-allowed disabled:opacity-30"
        disabled={!canEdit}
        aria-label={dragAria}
        {...attributes}
        {...listeners}
      >
        <IconGripVertical size={18} stroke={1.75} />
      </button>
      <span className="min-w-0 flex-1 text-slate-800">{label}</span>
    </li>
  )
}

export default function LeadsDistributionRulesPage() {
  const { t } = useI18n()
  const [base, setBase] = useState<LeadDistributionOut | null>(null)
  const [strategy, setStrategy] = useState<LeadDistributionOut['strategy']>('smart')
  const [criteriaOrder, setCriteriaOrder] = useState<string[]>(['working_hours', 'workload', 'language'])
  const [maxLeads, setMaxLeads] = useState(10)
  const [onlyActive, setOnlyActive] = useState(true)
  const [previewLang, setPreviewLang] = useState('pl')
  const [langRoute, setLangRoute] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await getLeadDistribution()
      setBase(d)
      setStrategy(d.strategy)
      setCriteriaOrder(d.criteria_order.length ? d.criteria_order : ['working_hours', 'workload', 'language'])
      setMaxLeads(d.max_leads_per_person)
      setOnlyActive(d.only_active_employees)
      setPreviewLang(d.preview_language || 'pl')
      setLangRoute({ ...(d.language_routing_v1 || {}) })
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      setError(err?.response?.data?.detail || err?.message || 'Failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const onDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const a = String(active.id)
    const o = String(over.id)
    setCriteriaOrder((prev) => {
      const oldIndex = prev.indexOf(a)
      const newIndex = prev.indexOf(o)
      if (oldIndex === -1 || newIndex === -1) return prev
      return arrayMove(prev, oldIndex, newIndex)
    })
  }, [])

  const toggleCriterion = (id: string) => {
    if (criteriaOrder.includes(id)) {
      setCriteriaOrder(criteriaOrder.filter((x) => x !== id))
    } else {
      setCriteriaOrder([...criteriaOrder, id])
    }
  }

  const criterionLabel = (id: string) => t(`app.leads.distribution.rules.criteria.${id}`)

  const toggleRouteUser = (lang: string, userId: string) => {
    if (!base) return
    const teamOrder = base.team.map((m) => m.user_id)
    setLangRoute((prev) => {
      const selected = new Set(prev[lang] ?? [])
      if (selected.has(userId)) selected.delete(userId)
      else selected.add(userId)
      const nextIds = teamOrder.filter((id) => selected.has(id))
      return { ...prev, [lang]: nextIds }
    })
  }

  const save = async () => {
    if (!base?.feature_gate.advanced_rules_allowed) return
    setSaving(true)
    setError(null)
    try {
      const d = await patchLeadDistribution({
        strategy,
        criteria_order: criteriaOrder.filter((x) => CRITERIA_IDS.includes(x as (typeof CRITERIA_IDS)[number])),
        max_leads_per_person: maxLeads,
        only_active_employees: onlyActive,
        preview_language: previewLang,
        language_routing_v1: langRoute,
      })
      setBase(d)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      setError(err?.response?.data?.detail || err?.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (loading || !base) {
    return (
      <div className="px-4 py-8 text-sm text-slate-600">{loading ? t('common.loading') : (error ?? '')}</div>
    )
  }

  const canEdit = base.feature_gate.advanced_rules_allowed

  return (
    <div className="mx-auto max-w-xl space-y-6 px-4 py-6">
      <Link to={CRM_APP_PATHS.leadsDistribution} className="text-xs font-medium text-brand-700 hover:underline">
        ← {t('app.leads.distribution.rules.back')}
      </Link>
      <h1 className="text-2xl font-semibold text-slate-900">{t('app.leads.distribution.rules.title')}</h1>

      {!canEdit ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          🔒 {t('app.leads.distribution.rules.locked')}{' '}
          <Link className="font-medium underline" to={`${ACTIVATION_PATHS.billing}?focus=plan`}>
            {t('app.leads.distribution.rules.upgrade')}
          </Link>
        </div>
      ) : null}

      {error ? <div className="text-sm text-rose-700">{String(error)}</div> : null}

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-medium text-slate-800">{t('app.leads.distribution.rules.strategy')}</h2>
        <div className="mt-3 space-y-2 text-sm">
          {(
            [
              ['smart', t('app.leads.distribution.rules.smart')],
              ['round_robin', t('app.leads.distribution.rules.rr')],
              ['manual_rules', t('app.leads.distribution.rules.manual_rules')],
            ] as const
          ).map(([val, label]) => (
            <label key={val} className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="strat"
                value={val}
                checked={strategy === val}
                disabled={!canEdit}
                onChange={() => setStrategy(val)}
              />
              {label}
            </label>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-medium text-slate-800">{t('app.leads.distribution.rules.priority')}</h2>
        <p className="mt-1 text-xs text-slate-500">{t('app.leads.distribution.rules.priority_hint')}</p>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={criteriaOrder} strategy={verticalListSortingStrategy}>
            <ul className="mt-3 space-y-2">
              {criteriaOrder.map((id, idx) => (
                <SortableCriterionRow
                  key={id}
                  id={id}
                  index={idx}
                  label={criterionLabel(id)}
                  canEdit={canEdit}
                  dragAria={t('app.leads.distribution.rules.drag_handle_aria')}
                />
              ))}
            </ul>
          </SortableContext>
        </DndContext>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {CRITERIA_IDS.filter((id) => !criteriaOrder.includes(id)).map((id) => (
            <button
              key={id}
              type="button"
              disabled={!canEdit}
              className="rounded-full border border-dashed border-slate-300 px-2 py-1 hover:bg-slate-50 disabled:opacity-40"
              onClick={() => toggleCriterion(id)}
            >
              + {criterionLabel(id)}
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-medium text-slate-800">{t('app.leads.distribution.rules.limits')}</h2>
        <label className="mt-3 block text-sm text-slate-700">
          {t('app.leads.distribution.rules.max')}
          <input
            type="number"
            min={1}
            max={500}
            disabled={!canEdit}
            value={maxLeads}
            onChange={(e) => setMaxLeads(Number(e.target.value) || 1)}
            className="mt-1 block w-32 rounded-lg border border-slate-300 px-2 py-1.5"
          />
        </label>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={onlyActive} disabled={!canEdit} onChange={(e) => setOnlyActive(e.target.checked)} />
          {t('app.leads.distribution.rules.only_active')}
        </label>
        <label className="mt-3 block text-sm text-slate-700">
          {t('app.leads.distribution.rules.preview_lang')}
          <select
            className="mt-1 block w-full rounded-lg border border-slate-300 px-2 py-1.5"
            value={previewLang}
            disabled={!canEdit}
            onChange={(e) => setPreviewLang(e.target.value)}
          >
            <option value="pl">PL</option>
            <option value="en">EN</option>
            <option value="de">DE</option>
          </select>
        </label>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-medium text-slate-800">{t('app.leads.distribution.rules.lang_route_title')}</h2>
        <p className="mt-1 text-xs text-slate-500">{t('app.leads.distribution.rules.lang_route_hint')}</p>
        <div className="mt-4 space-y-4">
          {!base.team?.length ? (
            <p className="text-sm text-slate-500">{t('app.leads.distribution.rules.lang_route_empty_team')}</p>
          ) : (
            ROUTE_LANGS.map((lang) => (
              <div key={lang}>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">{lang}</div>
                <div className="mt-2 space-y-1.5">
                  {base.team.map((m) => (
                    <label key={`${lang}-${m.user_id}`} className="flex cursor-pointer items-center gap-2 text-sm text-slate-800">
                      <input
                        type="checkbox"
                        disabled={!canEdit}
                        checked={(langRoute[lang] ?? []).includes(m.user_id)}
                        onChange={() => toggleRouteUser(lang, m.user_id)}
                      />
                      <span>{m.display_name}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      <button type="button" disabled={!canEdit || saving} className="btn-primary w-full rounded-lg py-2" onClick={() => void save()}>
        {saving ? t('common.saving') : t('common.actions.save')}
      </button>
    </div>
  )
}
