import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createAcquisitionActivity } from '../../api/searchAcquisition'
import { recruitmentSearchAcquisitionPath, recruitmentSearchMetaSourcePath } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useSearchWorkspace } from './SearchWorkspaceLayout'

const CHANNEL_OPTIONS = [
  { id: 'meta', label: 'Meta Ads', hint: 'Facebook и Instagram' },
  { id: 'google', label: 'Google Ads', hint: 'Скоро', disabled: true },
  { id: 'tiktok', label: 'TikTok Ads', hint: 'Скоро', disabled: true },
  { id: 'telegram', label: 'Telegram', hint: 'Скоро', disabled: true },
  { id: 'referral', label: 'Рефералы', hint: 'Скоро', disabled: true },
] as const

export default function LaunchAcquisitionPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const navigate = useNavigate()
  const { searchId, searchName } = useSearchWorkspace()
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [channelType, setChannelType] = useState('meta')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleCreate() {
    const label = name.trim()
    if (!label) return
    setBusy(true)
    try {
      await createAcquisitionActivity(searchId, { type: channelType, name: label })
      setStep(3)
    } catch {
      notify({
        title: t('app.acquisition.launch_failed', { defaultValue: 'Не удалось создать источник' }),
        variant: 'error',
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5" data-testid="m1-launch-acquisition">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">
          {t('app.acquisition.launch_title', { defaultValue: 'Запуск новой рекламы' })}
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          {t('app.acquisition.launch_subtitle', {
            defaultValue: 'Подбор «{name}» — выберите канал и дайте понятное имя кампании.',
            values: { name: searchName },
          })}
        </p>

        {step === 1 ? (
          <div className="mt-6 space-y-3">
            <p className="text-sm font-medium text-slate-800">
              {t('app.acquisition.step_channel', { defaultValue: '1. Канал привлечения' })}
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {CHANNEL_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  disabled={Boolean(opt.disabled)}
                  onClick={() => setChannelType(opt.id)}
                  className={`rounded-xl border-2 p-4 text-left text-sm transition ${
                    channelType === opt.id
                      ? 'border-brand-400 bg-brand-50'
                      : 'border-slate-200 hover:border-slate-300'
                  } ${opt.disabled ? 'opacity-50' : ''}`}
                >
                  <p className="font-semibold text-slate-900">{opt.label}</p>
                  <p className="mt-0.5 text-slate-600">{opt.hint}</p>
                </button>
              ))}
            </div>
            <button type="button" className="btn-primary mt-4" onClick={() => setStep(2)}>
              {t('common.actions.continue', { defaultValue: 'Продолжить' })}
            </button>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="mt-6 space-y-4">
            <p className="text-sm font-medium text-slate-800">
              {t('app.acquisition.step_name', { defaultValue: '2. Название (как вы будете узнавать эту рекламу)' })}
            </p>
            <input
              className="input w-full max-w-md"
              placeholder={t('app.acquisition.name_placeholder', { defaultValue: 'Например: Польша' })}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn-secondary" onClick={() => setStep(1)}>
                {t('common.actions.back', { defaultValue: 'Назад' })}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={busy || !name.trim()}
                onClick={() => void handleCreate()}
              >
                {busy ? t('common.loading') : t('app.acquisition.step_connect', { defaultValue: '3. Создать и настроить' })}
              </button>
            </div>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="mt-6 space-y-4">
            <p className="text-sm text-slate-700">
              {t('app.acquisition.launch_done', {
                defaultValue: 'Источник создан. Подключите Meta и привяжите объявления к этому подбору.',
              })}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-primary"
                onClick={() => navigate(recruitmentSearchMetaSourcePath(searchId))}
              >
                {t('app.acquisition.setup_meta', { defaultValue: 'Настроить Meta' })}
              </button>
              <Link to={recruitmentSearchAcquisitionPath(searchId)} className="btn-secondary">
                {t('app.acquisition.back_to_list', { defaultValue: 'К привлечению' })}
              </Link>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  )
}
