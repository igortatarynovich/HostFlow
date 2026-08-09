import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconArrowRight, IconPackage, IconUserPlus } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SetupFlowChrome } from '../../components/setup/SetupFlowChrome'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { declareManualCandidateIntake } from '../../api/onboarding'
import { seedOnboardingDemo } from '../../api/client'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { deferSuccessPathMeta } from '../../hooks/useSuccessPathReadiness'

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
    id: 'sample',
    emoji: '🟧',
    titleKey: 'app.onboarding.setup.intake.sample.title',
    titleDefault: 'Sample data',
    subtitleKey: 'app.onboarding.setup.intake.sample.subtitle',
    subtitleDefault: 'Load example leads and try the product now — clear later in one click',
    enabled: true,
    testId: 'm1-setup-intake-sample',
  },
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

  async function onSelectSample() {
    setLoading(true)
    setError(null)
    try {
      deferSuccessPathMeta()
      await seedOnboardingDemo()
      navigate(CRM_APP_PATHS.leads, { replace: true })
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.onboarding.setup.intake.errors.sample', {
            defaultValue: 'Could not load sample data. Administrator role is required.',
          }),
          t,
        ),
      )
    } finally {
      setLoading(false)
    }
  }

  async function onSelectManual() {
    setLoading(true)
    setError(null)
    try {
      deferSuccessPathMeta()
      await declareManualCandidateIntake()
      // Manual intake unlocks Meta gate but does not create a lead — return to checklist
      // with a clear next CTA (sample data / continue) instead of an empty shell.
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
    if (card.id === 'sample') {
      void onSelectSample()
      return
    }
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
          'Выберите способ. Нет рекламы сейчас — загрузите sample data или начните вручную. Meta можно позже.',
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
                      <span className="rounded bg-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-600">
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
                ) : card.enabled && card.id === 'sample' ? (
                  <IconPackage size={20} className="mt-0.5 shrink-0 text-brand-600" aria-hidden />
                ) : card.enabled ? (
                  <IconArrowRight size={18} className="mt-1 shrink-0 text-slate-400" aria-hidden />
                ) : null}
              </button>
            )
          })}
        </div>

        {error ? <ErrorRecoveryBanner info={error} compact /> : null}

        <p className="text-center text-sm text-slate-600">
          <Link to="/faq#launch_troubleshooting" className="font-medium text-brand-700 hover:underline">
            {t('app.onboarding.setup.intake.faq_link', {
              defaultValue: 'Stuck? Launch FAQ — common problems and answers',
            })}
          </Link>
        </p>

        {loading ? (
          <p className="text-center text-sm text-slate-600" aria-live="polite">
            {t('common.loading')}
          </p>
        ) : null}
      </div>
    </SetupFlowChrome>
  )
}
