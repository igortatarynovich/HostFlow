import { useEffect, useState } from 'react'
import { CreateSearchFlowChrome } from '../../components/recruitment/CreateSearchFlowChrome'
import { SearchReadyPanel } from '../../components/recruitment/SearchReadyPanel'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { listOwnCompanies, getOnboardingStatus } from '../../api/client'
import {
  createLaunchSearch,
  type LaunchSearchResult,
  type SearchRole,
} from '../../services/createLaunchSearch'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { persistLaunchSearch } from '../../services/launchSearchSession'

import { useI18n } from '../../i18n'
import { useVacancyCategoryOptions } from '../../hooks/useVacancyCategoryOptions'

const TOTAL_STEPS = 3

function OptionCard({
  selected,
  onClick,
  children,
  testId,
}: {
  selected: boolean
  onClick: () => void
  children: React.ReactNode
  testId?: string
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      data-testid={testId}
      onClick={onClick}
      className={`w-full rounded-xl border-2 p-4 text-left text-sm transition ${
        selected
          ? 'border-brand-400 bg-brand-50/80 ring-2 ring-brand-200'
          : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      {children}
    </button>
  )
}

export default function CreateSearchWizardPage() {
  const { locale } = useI18n()
  const { options: roleOptions } = useVacancyCategoryOptions(locale, true)
  const [step, setStep] = useState(1)
  const [role, setRole] = useState<SearchRole | ''>('')
  const [roleOther, setRoleOther] = useState('')
  const [target, setTarget] = useState<'own' | 'client' | ''>('')
  const [clientName, setClientName] = useState('')
  const [ownCompanyName, setOwnCompanyName] = useState('')
  const [businessType, setBusinessType] = useState<'agency' | 'employer' | 'services'>('agency')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [result, setResult] = useState<LaunchSearchResult | null>(null)

  useEffect(() => {
    void Promise.all([listOwnCompanies(), getOnboardingStatus()])
      .then(([own, status]) => {
        const name = own.items?.[0]?.name
        if (name) setOwnCompanyName(String(name))
        if (status.business_type) setBusinessType(status.business_type)
        if (status.business_type === 'employer') setTarget('own')
      })
      .catch(() => undefined)
  }, [])

  async function onCreateSearch() {
    if (!role || !target) return
    if (target === 'client' && !clientName.trim()) return
    if (role === 'other' && !roleOther.trim()) return

    setLoading(true)
    setError(null)
    try {
      const created = await createLaunchSearch({
        role,
        roleOtherLabel: role === 'other' ? roleOther.trim() : undefined,
        target,
        clientName: target === 'client' ? clientName.trim() : undefined,
      })
      persistLaunchSearch(created)
      setResult(created)
      setStep(3)
    } catch (err) {
      setError(
        getFriendlyErrorInfo(err, 'Не удалось создать подбор. Попробуйте ещё раз.', undefined),
      )
    } finally {
      setLoading(false)
    }
  }

  if (step === 3 && result) {
    return (
      <CreateSearchFlowChrome step={3} totalSteps={TOTAL_STEPS} title="Подбор готов">
        <SearchReadyPanel
          searchId={result.searchId}
          searchName={result.name}
          publicUrl={result.publicUrl}
        />
      </CreateSearchFlowChrome>
    )
  }

  return (
    <CreateSearchFlowChrome
      step={step}
      totalSteps={TOTAL_STEPS}
      title={step === 1 ? 'Кого вы ищете?' : 'Для кого?'}
      subtitle={
        step === 1
          ? 'Выберите тип людей, которых хотите привлечь через рекламу или анкету.'
          : 'Укажите, для какой компании вы запускаете подбор кандидатов. Ссылка из этого мастера — для кандидатов, не для B2B-запроса клиента.'
      }
    >
      {step === 1 ? (
        <div className="space-y-4">
          <div className="grid gap-3" role="radiogroup" aria-label="Кого ищем">
            {roleOptions.map((opt) => (
              <OptionCard
                key={opt.id}
                selected={role === opt.id}
                onClick={() => setRole(opt.id)}
                testId={`m1-create-search-role-${opt.id}`}
              >
                <span className="font-medium text-slate-900">
                  {opt.emoji} {opt.title}
                </span>
                <span className="mt-1 block text-slate-600">{opt.subtitle}</span>
              </OptionCard>
            ))}
          </div>
          {role === 'other' ? (
            <input
              type="text"
              value={roleOther}
              onChange={(e) => setRoleOther(e.target.value)}
              placeholder="Например: Механик, Электрик"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              data-testid="m1-create-search-role-other-input"
            />
          ) : null}
          <div className="flex justify-end pt-2">
            <button
              type="button"
              disabled={!role || (role === 'other' && !roleOther.trim())}
              onClick={() => setStep(2)}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              data-testid="m1-create-search-continue"
            >
              Продолжить
            </button>
          </div>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="space-y-4">
          <div className="grid gap-3" role="radiogroup" aria-label="Для кого">
            <OptionCard
              selected={target === 'own'}
              onClick={() => setTarget('own')}
              testId="m1-create-search-for-own"
            >
              <span className="font-medium text-slate-900">Для своей компании</span>
              {ownCompanyName ? (
                <span className="mt-1 block text-slate-600">{ownCompanyName}</span>
              ) : null}
            </OptionCard>
            {businessType === 'agency' ? (
              <OptionCard
                selected={target === 'client'}
                onClick={() => setTarget('client')}
                testId="m1-create-search-for-client"
              >
                <span className="font-medium text-slate-900">Для клиента (подбор кандидатов)</span>
                <span className="mt-1 block text-sm text-slate-600">
                  Вакансия и анкета для кандидатов этого клиента. Это не B2B-форма запроса от транспортной компании.
                </span>
              </OptionCard>
            ) : null}
          </div>

          {target === 'client' ? (
            <label className="block text-sm">
              <span className="font-medium text-slate-700">Название клиента</span>
              <input
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="Poltrakt"
                className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                data-testid="m1-create-search-client-name"
              />
            </label>
          ) : null}

          {error ? <ErrorRecoveryBanner info={error} compact /> : null}

          <div className="flex flex-wrap justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Назад
            </button>
            <button
              type="button"
              disabled={
                loading ||
                !target ||
                (target === 'client' && !clientName.trim())
              }
              onClick={() => void onCreateSearch()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              data-testid="m1-create-search-submit"
            >
              {loading ? 'Готовим ссылку…' : 'Создать подбор'}
            </button>
          </div>
        </div>
      ) : null}
    </CreateSearchFlowChrome>
  )
}
