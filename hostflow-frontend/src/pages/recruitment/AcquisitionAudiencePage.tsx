import { useEffect, useState } from 'react'
import { updateAcquisitionAudience, type AcquisitionAudience } from '../../api/searchAcquisition'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useSearchWorkspace } from './SearchWorkspaceLayout'
import { useAcquisitionOutlet } from './useAcquisitionOutlet'

function splitList(value: string): string[] {
  return value
    .split(/[,;\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function joinList(items?: string[]): string {
  return (items ?? []).join(', ')
}

export default function AcquisitionAudiencePage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const { searchId } = useSearchWorkspace()
  const { snapshot, loading, refresh } = useAcquisitionOutlet()
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({
    countries: '',
    age_min: '',
    age_max: '',
    experience: '',
    languages: '',
    gender: '',
    interests: '',
    notes: '',
  })

  useEffect(() => {
    const aud = snapshot?.audience
    if (!aud) return
    setForm({
      countries: joinList(aud.countries),
      age_min: aud.age_min != null ? String(aud.age_min) : '',
      age_max: aud.age_max != null ? String(aud.age_max) : '',
      experience: aud.experience ?? '',
      languages: joinList(aud.languages),
      gender: aud.gender ?? '',
      interests: joinList(aud.interests),
      notes: aud.notes ?? '',
    })
  }, [snapshot?.audience])

  async function handleSave() {
    setBusy(true)
    const payload: AcquisitionAudience = {
      countries: splitList(form.countries),
      languages: splitList(form.languages),
      interests: splitList(form.interests),
      experience: form.experience.trim() || null,
      gender: form.gender.trim() || null,
      notes: form.notes.trim() || null,
      age_min: form.age_min ? Number(form.age_min) : null,
      age_max: form.age_max ? Number(form.age_max) : null,
    }
    try {
      await updateAcquisitionAudience(searchId, payload)
      await refresh()
      notify({
        title: t('app.acquisition.audience_saved', { defaultValue: 'Стратегия аудитории сохранена' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.acquisition.audience_save_failed', { defaultValue: 'Не удалось сохранить аудиторию' }),
        variant: 'error',
      })
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p>
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" data-testid="m1-acquisition-audience">
      <h3 className="text-base font-semibold text-slate-900">
        {t('app.acquisition.audience_title', { defaultValue: 'Кого мы сейчас ищем?' })}
      </h3>
      <p className="mt-1 text-sm text-slate-600">
        {t('app.acquisition.audience_subtitle', {
          defaultValue: 'Стратегия таргетинга для рекламы. Позже HostFlow сможет создавать аудитории автоматически.',
        })}
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium text-slate-800">
            {t('app.acquisition.audience_countries', { defaultValue: 'Страны' })}
          </span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={form.countries}
            onChange={(e) => setForm((f) => ({ ...f, countries: e.target.value }))}
            placeholder="Польша, Украина, Беларусь"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-800">
            {t('app.acquisition.audience_age_min', { defaultValue: 'Возраст от' })}
          </span>
          <input
            type="number"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={form.age_min}
            onChange={(e) => setForm((f) => ({ ...f, age_min: e.target.value }))}
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-800">
            {t('app.acquisition.audience_age_max', { defaultValue: 'Возраст до' })}
          </span>
          <input
            type="number"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={form.age_max}
            onChange={(e) => setForm((f) => ({ ...f, age_max: e.target.value }))}
          />
        </label>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium text-slate-800">
            {t('app.acquisition.audience_experience', { defaultValue: 'Опыт' })}
          </span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={form.experience}
            onChange={(e) => setForm((f) => ({ ...f, experience: e.target.value }))}
            placeholder="CE, 2+ года в ЕС"
          />
        </label>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium text-slate-800">
            {t('app.acquisition.audience_languages', { defaultValue: 'Языки' })}
          </span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={form.languages}
            onChange={(e) => setForm((f) => ({ ...f, languages: e.target.value }))}
            placeholder="русский, польский, украинский"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-800">
            {t('app.acquisition.audience_gender', { defaultValue: 'Пол' })}
          </span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={form.gender}
            onChange={(e) => setForm((f) => ({ ...f, gender: e.target.value }))}
          />
        </label>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium text-slate-800">
            {t('app.acquisition.audience_interests', { defaultValue: 'Интересы' })}
          </span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={form.interests}
            onChange={(e) => setForm((f) => ({ ...f, interests: e.target.value }))}
          />
        </label>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium text-slate-800">
            {t('app.acquisition.audience_notes', { defaultValue: 'Заметки' })}
          </span>
          <textarea
            rows={3}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={form.notes}
            onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          />
        </label>
      </div>

      <button
        type="button"
        disabled={busy}
        onClick={() => void handleSave()}
        className="mt-6 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {busy ? t('common.loading', { defaultValue: 'Загрузка…' }) : t('common.save', { defaultValue: 'Сохранить' })}
      </button>
    </section>
  )
}
