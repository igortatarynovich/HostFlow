import { useState } from 'react'
import { CreateClientChannelFlowChrome } from '../../components/client-acquisition/CreateClientChannelFlowChrome'
import { ClientChannelReadyPanel } from '../../components/client-acquisition/ClientChannelReadyPanel'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import {
  createClientAcquisitionChannel,
  type ClientAcquisitionChannelResult,
} from '../../services/createClientAcquisitionChannel'
import { persistClientChannel } from '../../services/clientChannelSession'
import {
  CLIENT_AUDIENCE_OPTIONS,
  CLIENT_SERVICE_OPTIONS,
  type ClientAudience,
  type ClientService,
} from '../../utils/clientAcquisitionDefaults'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

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

function ServiceCheckbox({
  checked,
  onChange,
  label,
  testId,
}: {
  checked: boolean
  onChange: () => void
  label: string
  testId?: string
}) {
  return (
    <label
      className={`flex cursor-pointer items-center gap-3 rounded-xl border-2 px-4 py-3 text-sm transition ${
        checked ? 'border-brand-400 bg-brand-50/80' : 'border-slate-200 hover:border-slate-300'
      }`}
      data-testid={testId}
    >
      <input type="checkbox" checked={checked} onChange={onChange} className="h-4 w-4 rounded border-slate-300" />
      <span className="font-medium text-slate-900">{label}</span>
    </label>
  )
}

export default function CreateClientChannelWizardPage() {
  const { t } = useI18n()
  const [step, setStep] = useState(1)
  const [audience, setAudience] = useState<ClientAudience | ''>('')
  const [services, setServices] = useState<ClientService[]>([])
  const [serviceOther, setServiceOther] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [result, setResult] = useState<ClientAcquisitionChannelResult | null>(null)

  function toggleService(id: ClientService) {
    setServices((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]))
  }

  async function onCreateChannel() {
    if (!audience || !services.length) return
    if (services.includes('other') && !serviceOther.trim()) return

    setLoading(true)
    setError(null)
    try {
      const created = await createClientAcquisitionChannel({
        audience,
        services,
        serviceOtherLabel: services.includes('other') ? serviceOther.trim() : undefined,
      })
      persistClientChannel(created)
      setResult(created)
      setStep(3)
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.client_acquisition.wizard.create_failed', {
            defaultValue: 'Could not create the channel. Please try again.',
          }),
          t,
        ),
      )
    } finally {
      setLoading(false)
    }
  }

  if (step === 3 && result) {
    return (
      <CreateClientChannelFlowChrome
        step={3}
        totalSteps={TOTAL_STEPS}
        title={t('app.client_acquisition.wizard.done_title', { defaultValue: 'Acquisition ready' })}
      >
        <ClientChannelReadyPanel
          channelId={result.channelId}
          channelName={result.name}
          publicUrl={result.publicUrl}
        />
      </CreateClientChannelFlowChrome>
    )
  }

  return (
    <CreateClientChannelFlowChrome
      step={step}
      totalSteps={TOTAL_STEPS}
      title={
        step === 1
          ? t('app.client_acquisition.wizard.audience_title', {
              defaultValue: 'Who do you want to attract?',
            })
          : t('app.client_acquisition.wizard.services_title', {
              defaultValue: 'Which services do you offer?',
            })
      }
      subtitle={
        step === 1
          ? t('app.client_acquisition.wizard.audience_subtitle', {
              defaultValue: 'Choose the type of companies that should submit staffing inquiries.',
            })
          : t('app.client_acquisition.wizard.services_subtitle', {
              defaultValue: 'The company should understand what you are offering.',
            })
      }
    >
      {step === 1 ? (
        <div className="space-y-4">
          <div
            className="grid gap-3"
            role="radiogroup"
            aria-label={t('app.client_acquisition.wizard.audience_aria', {
              defaultValue: 'Who we attract',
            })}
          >
            {CLIENT_AUDIENCE_OPTIONS.map((opt) => (
              <OptionCard
                key={opt.id}
                selected={audience === opt.id}
                onClick={() => setAudience(opt.id)}
                testId={`m1-create-client-channel-audience-${opt.id}`}
              >
                <span className="font-medium text-slate-900">
                  {opt.emoji}{' '}
                  {t(`app.client_acquisition.audience.${opt.id}.title`, {
                    defaultValue: opt.title,
                  })}
                </span>
                <span className="mt-1 block text-slate-600">
                  {t(`app.client_acquisition.audience.${opt.id}.subtitle`, {
                    defaultValue: opt.subtitle,
                  })}
                </span>
              </OptionCard>
            ))}
          </div>
          <div className="flex justify-end pt-2">
            <button
              type="button"
              disabled={!audience}
              onClick={() => setStep(2)}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              data-testid="m1-create-client-channel-continue"
            >
              {t('common.continue', { defaultValue: 'Continue' })}
            </button>
          </div>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="space-y-4">
          <div className="grid gap-3">
            {CLIENT_SERVICE_OPTIONS.map((opt) => (
              <ServiceCheckbox
                key={opt.id}
                checked={services.includes(opt.id)}
                onChange={() => toggleService(opt.id)}
                label={t(`app.client_acquisition.services.${opt.id}`, {
                  defaultValue: opt.title,
                })}
                testId={`m1-create-client-channel-service-${opt.id}`}
              />
            ))}
          </div>
          {services.includes('other') ? (
            <input
              type="text"
              value={serviceOther}
              onChange={(e) => setServiceOther(e.target.value)}
              placeholder={t('app.client_acquisition.wizard.service_other_placeholder', {
                defaultValue: 'Describe the service',
              })}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              data-testid="m1-create-client-channel-service-other-input"
            />
          ) : null}

          {error ? <ErrorRecoveryBanner info={error} compact /> : null}

          <div className="flex flex-wrap justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              {t('common.back', { defaultValue: 'Back' })}
            </button>
            <button
              type="button"
              disabled={
                loading ||
                !services.length ||
                (services.includes('other') && !serviceOther.trim())
              }
              onClick={() => void onCreateChannel()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              data-testid="m1-create-client-channel-submit"
            >
              {loading
                ? t('app.client_acquisition.wizard.preparing_link', {
                    defaultValue: 'Preparing link…',
                  })
                : t('app.client_acquisition.wizard.get_link', { defaultValue: 'Get link' })}
            </button>
          </div>
        </div>
      ) : null}
    </CreateClientChannelFlowChrome>
  )
}
