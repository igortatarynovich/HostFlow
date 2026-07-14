import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { IconArrowRight, IconUserPlus } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SetupFlowChrome } from '../../components/setup/SetupFlowChrome'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { declareManualCandidateIntake } from '../../api/onboarding'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

type IntakeCard = {
  id: string
  emoji: string
  titleKey: string
  titleDefault: string
  subtitleKey: string
  subtitleDefault: string
  enabled: boolean
  soon?: boolean
  testId: string
}

const INTAKE_CARDS: IntakeCard[] = [
  {
    id: 'manual',
    emoji: '🟩',
    titleKey: 'app.onboarding.setup.intake.manual.title',
    titleDefault: 'Вручную',
    subtitleKey: 'app.onboarding.setup.intake.manual.subtitle',
    subtitleDefault: 'Добавлять кандидатов самостоятельно',
    enabled: true,
    testId: 'm1-setup-intake-manual',
  },
  {
    id: 'meta',
    emoji: '🟦',
    titleKey: 'app.onboarding.setup.intake.meta.title',
    titleDefault: 'Facebook / Instagram Ads',
    subtitleKey: 'app.onboarding.setup.intake.meta.subtitle',
    subtitleDefault: 'Подключить Meta',
    enabled: true,
    testId: 'm1-setup-intake-meta',
  },
  {
    id: 'website',
    emoji: '🟨',
    titleKey: 'app.onboarding.setup.intake.website.title',
    titleDefault: 'С сайта',
    subtitleKey: 'app.onboarding.setup.intake.website.subtitle',
    subtitleDefault: 'Форма на вашем сайте',
    enabled: false,
    soon: true,
    testId: 'm1-setup-intake-website',
  },
  {
    id: 'excel',
    emoji: '⬜',
    titleKey: 'app.onboarding.setup.intake.excel.title',
    titleDefault: 'Excel',
    subtitleKey: 'app.onboarding.setup.intake.excel.subtitle',
    subtitleDefault: 'Импорт списка кандидатов',
    enabled: false,
    soon: true,
    testId: 'm1-setup-intake-excel',
  },
  {
    id: 'api',
    emoji: '⬜',
    titleKey: 'app.onboarding.setup.intake.api.title',
    titleDefault: 'API',
    subtitleKey: 'app.onboarding.setup.intake.api.subtitle',
    subtitleDefault: 'Интеграция',
    enabled: false,
    soon: true,
    testId: 'm1-setup-intake-api',
  },
]

export default function SetupCandidateIntakePage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  async function onSelectManual() {
    setLoading(true)
    setError(null)
    try {
      const result = await declareManualCandidateIntake()
      if (result.setup_ready) {
        navigate(CRM_APP_PATHS.launchpad, { replace: true })
        return
      }
      navigate(CRM_APP_PATHS.setup, { replace: true })
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.onboarding.setup.intake.errors.generic', {
            defaultValue: 'Не удалось сохранить способ получения кандидатов.',
          }),
          t,
        ),
      )
    } finally {
      setLoading(false)
    }
  }

  function onSelectMeta() {
    navigate(CRM_APP_PATHS.settingsIntegrationsMeta)
  }

  function onSelectCard(card: IntakeCard) {
    if (!card.enabled || loading) return
    if (card.id === 'manual') {
      void onSelectManual()
      return
    }
    if (card.id === 'meta') {
      onSelectMeta()
    }
  }

  return (
    <SetupFlowChrome
      testId="m1-setup-intake-flow"
      stepLabel={t('app.onboarding.setup.intake.badge', { defaultValue: 'Настройка · Кандидаты' })}
      title={t('app.onboarding.setup.intake.title', {
        defaultValue: 'Как вы хотите получать первых кандидатов?',
      })}
      subtitle={t('app.onboarding.setup.intake.subtitle', {
        defaultValue:
          'Выберите способ появления кандидатов в системе. Можно начать вручную — Meta подключите позже.',
      })}
    >
      <div className="space-y-4">
        <div className="grid gap-3" role="list">
          {INTAKE_CARDS.map((card) => {
            const disabled = !card.enabled || loading
            return (
              <button
                key={card.id}
                type="button"
                role="listitem"
                data-testid={card.testId}
                data-enabled={card.enabled ? 'true' : 'false'}
                disabled={disabled}
                onClick={() => onSelectCard(card)}
                className={`flex w-full items-start gap-3 rounded-xl border-2 p-4 text-left transition ${
                  card.enabled
                    ? 'border-slate-200 bg-white hover:border-brand-300 hover:bg-brand-50/40'
                    : 'cursor-not-allowed border-slate-100 bg-slate-50 opacity-70'
                } disabled:opacity-50`}
              >
                <span className="text-xl leading-none" aria-hidden>
                  {card.emoji}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-900">
                      {t(card.titleKey, { defaultValue: card.titleDefault })}
                    </span>
                    {card.soon ? (
                      <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-600">
                        {t('app.onboarding.setup.intake.soon', { defaultValue: 'Скоро' })}
                      </span>
                    ) : null}
                  </span>
                  <span className="mt-0.5 block text-sm text-slate-600">
                    {t(card.subtitleKey, { defaultValue: card.subtitleDefault })}
                  </span>
                </span>
                {card.enabled && card.id === 'manual' ? (
                  <IconUserPlus size={20} className="mt-0.5 shrink-0 text-brand-600" aria-hidden />
                ) : card.enabled ? (
                  <IconArrowRight size={18} className="mt-1 shrink-0 text-slate-400" aria-hidden />
                ) : null}
              </button>
            )
          })}
        </div>

        {error ? <ErrorRecoveryBanner info={error} compact /> : null}

        {loading ? (
          <p className="text-center text-sm text-slate-600" aria-live="polite">
            {t('common.loading')}
          </p>
        ) : null}
      </div>
    </SetupFlowChrome>
  )
}
