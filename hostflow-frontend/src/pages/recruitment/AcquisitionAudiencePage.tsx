/**
 * C-7: audience strategy on Подборы is read-only — edits belong in Marketing.
 */
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useAcquisitionOutlet } from './useAcquisitionOutlet'

function joinList(items?: string[]): string {
  return (items ?? []).join(', ') || '—'
}

export default function AcquisitionAudiencePage() {
  const { t } = useI18n()
  const { snapshot, loading } = useAcquisitionOutlet()
  const aud = snapshot?.audience
  const marketingHref = snapshot?.marketing_setup_path || CRM_APP_PATHS.marketing

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p>
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm" data-testid="m1-acquisition-audience">
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
        {t('app.acquisition.audience_readonly', {
          defaultValue:
            'Редактирование аудитории в Подборах отключено. Настройки таргетинга ведутся в Marketing (Campaign → Flight).',
        })}{' '}
        <Link to={marketingHref} className="font-medium text-brand-700 underline">
          {t('app.acquisition.go_marketing_setup', { defaultValue: 'Открыть Marketing' })}
        </Link>
      </div>

      <h3 className="mt-4 text-base font-semibold text-slate-900">
        {t('app.acquisition.audience_title', { defaultValue: 'Кого мы сейчас ищем?' })}
      </h3>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">{t('app.acquisition.audience_countries', { defaultValue: 'Страны' })}</dt>
          <dd className="font-medium text-slate-900">{joinList(aud?.countries)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">{t('app.acquisition.audience_age', { defaultValue: 'Возраст' })}</dt>
          <dd className="font-medium text-slate-900">
            {aud?.age_min != null || aud?.age_max != null
              ? `${aud?.age_min ?? '—'} – ${aud?.age_max ?? '—'}`
              : '—'}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">{t('app.acquisition.audience_experience', { defaultValue: 'Опыт' })}</dt>
          <dd className="font-medium text-slate-900">{aud?.experience || '—'}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">{t('app.acquisition.audience_languages', { defaultValue: 'Языки' })}</dt>
          <dd className="font-medium text-slate-900">{joinList(aud?.languages)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">{t('app.acquisition.audience_gender', { defaultValue: 'Пол' })}</dt>
          <dd className="font-medium text-slate-900">{aud?.gender || '—'}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">{t('app.acquisition.audience_interests', { defaultValue: 'Интересы' })}</dt>
          <dd className="font-medium text-slate-900">{joinList(aud?.interests)}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">{t('app.acquisition.audience_notes', { defaultValue: 'Заметки' })}</dt>
          <dd className="font-medium text-slate-900">{aud?.notes || '—'}</dd>
        </div>
      </dl>
    </section>
  )
}
