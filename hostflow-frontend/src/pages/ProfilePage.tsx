import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ChangeEvent, DragEvent, FormEvent } from 'react'
import {
  changeSelfPassword,
  listUserSessions,
  patchUserMe,
  revokeUserSessions,
  updateNotificationPreferences,
  uploadUserAvatar,
} from '../api/users'
import { listCompanies } from '../api/client'
import type {
  Company,
  UserNotificationPreference,
  UserPreferences,
  UserSavedViews,
  UserSessionInfo,
} from '../api/types'
import { useAuth } from '../store/useAuth'
import { useI18n, type LocaleCode } from '../i18n'

const LOCALE_OPTIONS = ['ru-RU', 'pl-PL', 'en-US']
const TIMEZONE_OPTIONS = ['Europe/Warsaw', 'Europe/Moscow', 'UTC']
const DATE_FORMAT_OPTIONS = ['DD.MM.YYYY', 'YYYY-MM-DD', 'MM/DD/YYYY']
const PHONE_FORMAT_OPTIONS = ['+CC (AAA) BBB-CC-DD', '+CC BBB BBB BBB', '+CC BBBBB BBBBB']
const THEME_VALUES = ['system', 'light', 'dark'] as const

const NOTIFICATION_ITEMS = [
  { code: 'candidate.new_assignment', key: 'candidate_new_assignment' },
  { code: 'candidate.stage_changed', key: 'candidate_stage_changed' },
  { code: 'documents.deadline', key: 'documents_deadline' },
  { code: 'mentions.direct', key: 'mentions_direct' },
  { code: 'lead.new.telegram', key: 'lead_new_telegram' },
  { code: 'lead.status_changed.telegram', key: 'lead_status_changed_telegram' },
] as const

type NotificationItemKey = (typeof NOTIFICATION_ITEMS)[number]['key']

const FREQUENCY_VALUES: UserNotificationPreference['mode'][] = ['immediate', 'daily_digest']

function generateViewId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `view-${Date.now()}`
}

function cloneSavedViews(prefs?: UserPreferences): UserSavedViews {
  return {
    candidates: (prefs?.saved_views?.candidates ?? []).map((view) => ({ ...view, filters: { ...(view.filters ?? {}) } })),
    vacancies: (prefs?.saved_views?.vacancies ?? []).map((view) => ({ ...view, filters: { ...(view.filters ?? {}) } })),
  }
}

type SavedViewsModule = keyof UserSavedViews

const SAVED_VIEW_MODULES: SavedViewsModule[] = ['candidates', 'vacancies']

export default function ProfilePage() {
  const {
    me,
    preferences,
    security,
    sessionId,
    refresh,
    updateProfile,
    updatePreferences,
    updateSecurity,
  } = useAuth()
  const { t, setLocale } = useI18n()

  const [companies, setCompanies] = useState<Company[]>([])

  const [profileForm, setProfileForm] = useState({
    first_name: me?.first_name ?? '',
    last_name: me?.last_name ?? '',
    position: me?.position ?? '',
    phone: me?.phone ?? '',
    email: me?.email ?? '',
    country: me?.country ?? '',
    city: me?.city ?? '',
    birth_date: me?.birth_date ?? '',
  })

  const [avatarPreview, setAvatarPreview] = useState<string | null>(me?.avatar_url ?? null)
  const [avatarUploading, setAvatarUploading] = useState(false)

  const [uiForm, setUiForm] = useState({
    locale: preferences?.ui?.locale ?? LOCALE_OPTIONS[0],
    timezone: preferences?.ui?.timezone ?? TIMEZONE_OPTIONS[0],
    date_format: preferences?.ui?.date_format ?? DATE_FORMAT_OPTIONS[0],
    phone_format: preferences?.ui?.phone_format ?? PHONE_FORMAT_OPTIONS[0],
    theme: preferences?.ui?.theme ?? 'system',
  })

  const [defaultCompany, setDefaultCompany] = useState<string>(preferences?.defaults?.company_id ?? '')
  const [savedViews, setSavedViews] = useState<UserSavedViews>(() => cloneSavedViews(preferences ?? undefined))
  const [notificationState, setNotificationState] = useState<Record<string, UserNotificationPreference>>(
    () => ({ ...preferences?.notifications }),
  )

  const [sessions, setSessions] = useState<UserSessionInfo[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)

  const [profileMessage, setProfileMessage] = useState<string | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [profileSaving, setProfileSaving] = useState(false)

  const [prefsMessage, setPrefsMessage] = useState<string | null>(null)
  const [prefsError, setPrefsError] = useState<string | null>(null)
  const [prefsSaving, setPrefsSaving] = useState(false)

  const [notifMessage, setNotifMessage] = useState<string | null>(null)
  const [notifError, setNotifError] = useState<string | null>(null)
  const [notifSaving, setNotifSaving] = useState(false)

  const [passwordForm, setPasswordForm] = useState({ current: '', next: '', confirm: '' })
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordSaving, setPasswordSaving] = useState(false)
  const savedViewLabels = useMemo<Record<SavedViewsModule, string>>(
    () => ({
      candidates: t('app.profile.saved_views.modules.candidates'),
      vacancies: t('app.profile.saved_views.modules.vacancies'),
    }),
    [t]
  )
  const notificationLabels = useMemo<Record<NotificationItemKey, { title: string; description: string }>>(() => {
    const entries: Record<NotificationItemKey, { title: string; description: string }> = {
      candidate_new_assignment: { title: '', description: '' },
      candidate_stage_changed: { title: '', description: '' },
      documents_deadline: { title: '', description: '' },
      mentions_direct: { title: '', description: '' },
      lead_new_telegram: { title: '', description: '' },
      lead_status_changed_telegram: { title: '', description: '' },
    }
    const defaults: Record<NotificationItemKey, { title: string; description: string }> = {
      candidate_new_assignment: {
        title: 'New candidate assignment',
        description: 'Receive notification when a candidate is assigned to you.',
      },
      candidate_stage_changed: {
        title: 'Candidate stage changed',
        description: 'Receive notification when candidate stage is updated.',
      },
      documents_deadline: {
        title: 'Document deadline',
        description: 'Receive reminder before document deadline.',
      },
      mentions_direct: {
        title: 'Direct mentions',
        description: 'Receive notification when someone mentions you.',
      },
      lead_new_telegram: {
        title: 'Telegram: new lead',
        description: 'Send Telegram alert when a new lead is created (especially for services flow).',
      },
      lead_status_changed_telegram: {
        title: 'Telegram: lead status changed',
        description: 'Send Telegram alert when lead status changes.',
      },
    }
    NOTIFICATION_ITEMS.forEach((item) => {
      entries[item.key] = {
        title: t(`app.profile.notifications.items.${item.key}.title`, { defaultValue: defaults[item.key].title }),
        description: t(`app.profile.notifications.items.${item.key}.description`, { defaultValue: defaults[item.key].description }),
      }
    })
    return entries
  }, [t])
  const frequencyOptions = useMemo(
    () =>
      FREQUENCY_VALUES.map((value) => ({
        value,
        label: t(`app.profile.notifications.frequency.${value}`),
      })),
    [t]
  )
  const themeOptions = useMemo(
    () =>
      THEME_VALUES.map((value) => ({
        value,
        label: t(`app.profile.theme.${value}`),
      })),
    [t]
  )

  useEffect(() => {
    setProfileForm({
      first_name: me?.first_name ?? '',
      last_name: me?.last_name ?? '',
      position: me?.position ?? '',
      phone: me?.phone ?? '',
      email: me?.email ?? '',
      country: me?.country ?? '',
      city: me?.city ?? '',
      birth_date: me?.birth_date ?? '',
    })
    setAvatarPreview(me?.avatar_url ?? null)
  }, [me?.first_name, me?.last_name, me?.position, me?.phone, me?.email, me?.country, me?.city, me?.birth_date, me?.avatar_url])

  useEffect(() => {
    setUiForm({
      locale: preferences?.ui?.locale ?? LOCALE_OPTIONS[0],
      timezone: preferences?.ui?.timezone ?? TIMEZONE_OPTIONS[0],
      date_format: preferences?.ui?.date_format ?? DATE_FORMAT_OPTIONS[0],
      phone_format: preferences?.ui?.phone_format ?? PHONE_FORMAT_OPTIONS[0],
      theme: preferences?.ui?.theme ?? 'system',
    })
    setDefaultCompany(preferences?.defaults?.company_id ?? '')
    setSavedViews(cloneSavedViews(preferences ?? undefined))
    setNotificationState({ ...(preferences?.notifications ?? {}) })
  }, [preferences])

  useEffect(() => {
    listCompanies({ limit: 200, offset: 0 })
      .then((response: any) => {
        const items: any[] = Array.isArray(response?.items) ? response.items : (Array.isArray(response) ? response : [])
        const mapped: Company[] = items.map((item: any) => ({ id: item.id || item.uuid, name: item.name || item.title || '—' }))
          .filter((item) => item.id)
        setCompanies(mapped)
      })
      .catch((err) => console.warn('[ProfilePage] listCompanies failed', err))
  }, [])

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true)
    try {
      const result = await listUserSessions()
      setSessions(result)
    } catch (err) {
      console.warn('[ProfilePage] list sessions failed', err)
      setSessions([])
    } finally {
      setSessionsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSessions().catch(() => undefined)
  }, [loadSessions])

  const handleProfileChange = (key: keyof typeof profileForm) => (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value
    setProfileForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleUiChange = (key: keyof typeof uiForm) => (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value
    setUiForm((prev) => ({ ...prev, [key]: value }))
    if (key === 'locale') {
      const short = value.split('-')[0].toLowerCase()
      if (short === 'ru' || short === 'en' || short === 'pl') {
        setLocale(short as LocaleCode)
      }
    }
  }

  const handleNotificationToggle = (code: string) => (event: ChangeEvent<HTMLInputElement>) => {
    setNotificationState((prev) => ({
      ...prev,
      [code]: {
        enabled: event.target.checked,
        mode: prev[code]?.mode ?? 'immediate',
      },
    }))
  }

  const handleNotificationMode = (code: string, mode: UserNotificationPreference['mode']) => {
    setNotificationState((prev) => ({
      ...prev,
      [code]: {
        enabled: prev[code]?.enabled ?? true,
        mode,
      },
    }))
  }

  const handleAddSavedView = (module: SavedViewsModule) => {
    const name = window.prompt(t('app.profile.saved_views.prompts.add', { values: { module: savedViewLabels[module] } }))
    if (!name) return
    const filtersInput = window.prompt(t('app.profile.saved_views.prompts.filters'), '{}') ?? '{}'
    let filters: Record<string, any> = {}
    try {
      filters = filtersInput.trim() ? JSON.parse(filtersInput) : {}
    } catch (err) {
      window.alert(t('app.profile.saved_views.prompts.filters_invalid'))
      return
    }
    setSavedViews((prev) => {
      const nextList = [...prev[module], { id: generateViewId(), name: name.trim(), filters, is_default: prev[module].length === 0 }]
      return { ...prev, [module]: nextList }
    })
  }

  const handleRenameSavedView = (module: SavedViewsModule, id: string) => {
    setSavedViews((prev) => {
      const nextList = prev[module].map((view) => {
        if (view.id !== id) return view
        const nextName = window.prompt(t('app.profile.saved_views.prompts.rename'), view.name)
        if (!nextName) return view
        return { ...view, name: nextName.trim() }
      })
      return { ...prev, [module]: nextList }
    })
  }

  const handleEditSavedViewFilters = (module: SavedViewsModule, id: string) => {
    setSavedViews((prev) => {
      const nextList = prev[module].map((view) => {
        if (view.id !== id) return view
        const current = JSON.stringify(view.filters ?? {}, null, 2)
        const nextStr = window.prompt(t('app.profile.saved_views.prompts.filters'), current)
        if (nextStr == null) return view
        try {
          const parsed = nextStr.trim() ? JSON.parse(nextStr) : {}
          return { ...view, filters: parsed }
        } catch (err) {
          window.alert(t('app.profile.saved_views.prompts.filters_invalid'))
          return view
        }
      })
      return { ...prev, [module]: nextList }
    })
  }

  const handleDeleteSavedView = (module: SavedViewsModule, id: string) => {
    setSavedViews((prev) => {
      const nextList = prev[module].filter((view) => view.id !== id)
      return { ...prev, [module]: nextList }
    })
  }

  const handleSetDefaultView = (module: SavedViewsModule, id: string) => {
    setSavedViews((prev) => {
      const nextList = prev[module].map((view) => ({ ...view, is_default: view.id === id }))
      return { ...prev, [module]: nextList }
    })
  }

  const handleProfileSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setProfileSaving(true)
    setProfileMessage(null)
    setProfileError(null)
    try {
      const payload = {
        profile: {
          ...profileForm,
          birth_date: profileForm.birth_date || null,
        },
      }
      const result = await patchUserMe(payload)
      updateProfile({
        first_name: result.profile.first_name,
        last_name: result.profile.last_name,
        position: result.profile.position,
        phone: result.profile.phone,
        email: result.profile.email,
        country: result.profile.country,
        city: result.profile.city,
        birth_date: result.profile.birth_date,
        avatar_url: result.profile.avatar_url,
      })
      updatePreferences(result.preferences)
      updateSecurity(result.security)
      setProfileMessage(t('app.profile.messages.profile_saved'))
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setProfileError(typeof detail === 'string' ? detail : t('app.profile.messages.profile_error'))
    } finally {
      setProfileSaving(false)
    }
  }

  const handleProfileReset = () => {
    setProfileForm({
      first_name: me?.first_name ?? '',
      last_name: me?.last_name ?? '',
      position: me?.position ?? '',
      phone: me?.phone ?? '',
      email: me?.email ?? '',
      country: me?.country ?? '',
      city: me?.city ?? '',
      birth_date: me?.birth_date ?? '',
    })
  }

  const handlePreferencesSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setPrefsSaving(true)
    setPrefsMessage(null)
    setPrefsError(null)
    try {
      const payload = {
        preferences: {
          ui: { ...uiForm },
          defaults: { company_id: defaultCompany || null },
          saved_views: {
            candidates: savedViews.candidates,
            vacancies: savedViews.vacancies,
          },
        },
      }
      const result = await patchUserMe(payload)
      updatePreferences(result.preferences)
      updateSecurity(result.security)
      setPrefsMessage(t('app.profile.messages.preferences_saved'))
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setPrefsError(typeof detail === 'string' ? detail : t('app.profile.messages.preferences_error'))
    } finally {
      setPrefsSaving(false)
    }
  }

  const handlePreferencesReset = () => {
    setUiForm({
      locale: preferences?.ui?.locale ?? LOCALE_OPTIONS[0],
      timezone: preferences?.ui?.timezone ?? TIMEZONE_OPTIONS[0],
      date_format: preferences?.ui?.date_format ?? DATE_FORMAT_OPTIONS[0],
      phone_format: preferences?.ui?.phone_format ?? PHONE_FORMAT_OPTIONS[0],
      theme: preferences?.ui?.theme ?? 'system',
    })
    setDefaultCompany(preferences?.defaults?.company_id ?? '')
    setSavedViews(cloneSavedViews(preferences ?? undefined))
  }

  const handleNotificationsSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setNotifSaving(true)
    setNotifMessage(null)
    setNotifError(null)
    try {
      const updated = await updateNotificationPreferences(notificationState)
      if (preferences) {
        updatePreferences({ ...preferences, notifications: updated })
      } else {
        await refresh()
      }
      setNotifMessage(t('app.profile.messages.notifications_saved'))
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setNotifError(typeof detail === 'string' ? detail : t('app.profile.messages.notifications_error'))
    } finally {
      setNotifSaving(false)
    }
  }

  const handleNotificationsReset = () => {
    setNotificationState({ ...(preferences?.notifications ?? {}) })
  }

  const handlePasswordSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setPasswordSaving(true)
    setPasswordMessage(null)
    setPasswordError(null)
    if (passwordForm.next !== passwordForm.confirm) {
      setPasswordError(t('app.profile.messages.password_mismatch'))
      setPasswordSaving(false)
      return
    }
    try {
      await changeSelfPassword({ current_password: passwordForm.current, new_password: passwordForm.next })
      setPasswordMessage(t('app.profile.messages.password_saved'))
      setPasswordForm({ current: '', next: '', confirm: '' })
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setPasswordError(typeof detail === 'string' ? detail : t('app.profile.messages.password_error'))
    } finally {
      setPasswordSaving(false)
    }
  }

  const handleAvatarFile = async (file: File | null) => {
    if (!file) return
    setAvatarUploading(true)
    try {
      const { avatar_url } = await uploadUserAvatar(file)
      updateProfile({ avatar_url })
      if (avatar_url) {
        setAvatarPreview(`${avatar_url}?v=${Date.now()}`)
      } else {
        setAvatarPreview(null)
      }
    } catch (err) {
      console.warn('[ProfilePage] avatar upload failed', err)
      window.alert(t('app.profile.messages.avatar_error'))
    } finally {
      setAvatarUploading(false)
    }
  }

  const onAvatarInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      void handleAvatarFile(file)
    }
  }

  const onAvatarDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault()
    const file = event.dataTransfer.files?.[0]
    if (file) {
      void handleAvatarFile(file)
    }
  }

  const handleSessionsRevoke = async () => {
    try {
      await revokeUserSessions()
      await loadSessions()
      await refresh()
    } catch (err) {
      console.warn('[ProfilePage] revoke sessions failed', err)
      window.alert(t('app.profile.messages.sessions_revoke_error'))
    }
  }

  const supervisorName = security?.supervisor?.name || security?.supervisor?.email || '—'

  const savedViewsByModule = useMemo(() => (module: SavedViewsModule) => savedViews[module], [savedViews])

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <header>
        <h1 className="text-3xl font-semibold text-slate-900">{t('app.profile.title')}</h1>
        <p className="mt-1 text-sm text-slate-500">{t('app.profile.subtitle')}</p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">{t('app.profile.sections.profile.title')}</h2>
          <p className="mb-4 mt-1 text-sm text-slate-500">{t('app.profile.sections.profile.description')}</p>

          <form className="space-y-4" onSubmit={handleProfileSubmit}>
            <div className="flex items-center gap-4">
              <label
                className="relative flex h-24 w-24 cursor-pointer items-center justify-center overflow-hidden rounded-full border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500"
                onDragOver={(event) => event.preventDefault()}
                onDrop={onAvatarDrop}
              >
                {avatarPreview ? (
                  <img src={avatarPreview} alt="Avatar" className="h-full w-full object-cover" />
                ) : (
                  <span>{t('app.profile.avatar.upload')}</span>
                )}
                <input type="file" accept="image/*" className="hidden" onChange={onAvatarInputChange} />
                {avatarUploading && (
                  <span className="absolute inset-0 grid place-items-center bg-white/70 text-xs">{t('common.loading')}</span>
                )}
              </label>
              <div className="text-sm text-slate-500">
                <p className="font-medium text-slate-700">{t('app.profile.avatar.label')}</p>
                <p>{t('app.profile.avatar.description')}</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Field label={t('app.profile.fields.first_name')}>
                <input className="input" value={profileForm.first_name} onChange={handleProfileChange('first_name')} autoComplete="given-name" />
              </Field>
              <Field label={t('app.profile.fields.last_name')}>
                <input className="input" value={profileForm.last_name} onChange={handleProfileChange('last_name')} autoComplete="family-name" />
              </Field>
              <Field label={t('app.profile.fields.position')}>
                <input className="input" value={profileForm.position} onChange={handleProfileChange('position')} autoComplete="organization-title" />
              </Field>
              <Field label={t('app.profile.fields.phone')}>
                <input className="input" value={profileForm.phone} onChange={handleProfileChange('phone')} autoComplete="tel" />
              </Field>
              <Field label={t('app.profile.fields.email')}>
                <input className="input" type="email" value={profileForm.email} onChange={handleProfileChange('email')} autoComplete="email" />
              </Field>
              <Field label={t('app.profile.fields.birth_date')}>
                <input className="input" type="date" value={profileForm.birth_date} onChange={handleProfileChange('birth_date')} />
              </Field>
              <Field label={t('app.profile.fields.country')}>
                <input className="input" value={profileForm.country} onChange={handleProfileChange('country')} autoComplete="country-name" />
              </Field>
              <Field label={t('app.profile.fields.city')}>
                <input className="input" value={profileForm.city} onChange={handleProfileChange('city')} autoComplete="address-level2" />
              </Field>
            </div>

            {profileMessage && <Alert variant="success" message={profileMessage} />}
            {profileError && <Alert variant="error" message={profileError} />}

            <div className="flex gap-3">
              <button type="submit" className="btn-primary" disabled={profileSaving}>{profileSaving ? t('common.saving') : t('common.actions.save')}</button>
              <button type="button" className="btn-secondary" onClick={handleProfileReset} disabled={profileSaving}>{t('common.actions.reset')}</button>
            </div>
          </form>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">{t('app.profile.sections.preferences.title')}</h2>
          <p className="mb-4 mt-1 text-sm text-slate-500">{t('app.profile.sections.preferences.description')}</p>

          <form className="space-y-4" onSubmit={handlePreferencesSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label={t('app.profile.preferences.labels.locale')}>
                <select className="input" value={uiForm.locale} onChange={handleUiChange('locale')}>
                  {LOCALE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </Field>
              <Field label={t('app.profile.preferences.labels.timezone')}>
                <select className="input" value={uiForm.timezone} onChange={handleUiChange('timezone')}>
                  {TIMEZONE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </Field>
              <Field label={t('app.profile.preferences.labels.date_format')}>
                <select className="input" value={uiForm.date_format} onChange={handleUiChange('date_format')}>
                  {DATE_FORMAT_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </Field>
              <Field label={t('app.profile.preferences.labels.phone_format')}>
                <select className="input" value={uiForm.phone_format} onChange={handleUiChange('phone_format')}>
                  {PHONE_FORMAT_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </Field>
              <Field label={t('app.profile.preferences.labels.theme')}>
                <select className="input" value={uiForm.theme} onChange={handleUiChange('theme')}>
                  {themeOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </Field>
              <Field label={t('app.profile.preferences.labels.default_company')}>
                <select className="input" value={defaultCompany} onChange={(event) => setDefaultCompany(event.target.value)}>
                  <option value="">{t('app.profile.preferences.company_placeholder')}</option>
                  {companies.map((company) => (
                    <option key={company.id} value={company.id}>{company.name}</option>
                  ))}
                </select>
              </Field>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-slate-700">{t('app.profile.saved_views.title')}</h3>
              <p className="mb-2 text-xs text-slate-500">{t('app.profile.saved_views.description')}</p>

              {SAVED_VIEW_MODULES.map((module) => (
                <div key={module} className="mb-4 rounded border border-slate-200 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-sm font-medium text-slate-800">{savedViewLabels[module]}</p>
                    <button type="button" className="btn-secondary btn-xs" onClick={() => handleAddSavedView(module)}>{t('app.profile.saved_views.add')}</button>
                  </div>
                  {savedViewsByModule(module).length === 0 ? (
                    <p className="text-xs text-slate-500">{t('app.profile.saved_views.empty')}</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {savedViewsByModule(module).map((view) => (
                        <li key={view.id} className="rounded border border-slate-200 p-3">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <p className="font-semibold text-slate-800">{view.name}</p>
                              <p className="mt-1 text-xs text-slate-500">{JSON.stringify(view.filters ?? {})}</p>
                              {view.is_default && <span className="mt-1 inline-block badge text-brand-700">{t('app.profile.saved_views.badge_default')}</span>}
                            </div>
                            <div className="flex flex-col items-end gap-1">
                              {!view.is_default && (
                                <button type="button" onClick={() => handleSetDefaultView(module, view.id)} className="btn-secondary btn-xs">{t('app.profile.saved_views.actions.set_default')}</button>
                              )}
                              <button type="button" onClick={() => handleRenameSavedView(module, view.id)} className="btn-secondary btn-xs">{t('app.profile.saved_views.actions.rename')}</button>
                              <button type="button" onClick={() => handleEditSavedViewFilters(module, view.id)} className="btn-secondary btn-xs">{t('app.profile.saved_views.actions.filters')}</button>
                              <button type="button" onClick={() => handleDeleteSavedView(module, view.id)} className="btn-danger btn-xs">{t('common.actions.delete')}</button>
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>

            {prefsMessage && <Alert variant="success" message={prefsMessage} />}
            {prefsError && <Alert variant="error" message={prefsError} />}

            <div className="flex gap-3">
              <button type="submit" className="btn-primary" disabled={prefsSaving}>{prefsSaving ? t('common.saving') : t('common.actions.save')}</button>
              <button type="button" className="btn-secondary" onClick={handlePreferencesReset} disabled={prefsSaving}>{t('common.actions.reset')}</button>
            </div>
          </form>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">{t('app.profile.sections.notifications.title')}</h2>
          <p className="mb-4 mt-1 text-sm text-slate-500">{t('app.profile.sections.notifications.description')}</p>

          <form className="space-y-4" onSubmit={handleNotificationsSubmit}>
            <div className="space-y-3">
              {NOTIFICATION_ITEMS.map((item) => (
                <div key={item.code} className="rounded border border-slate-200 p-3">
                  <div className="flex items-start justify-between gap-4">
                    <label className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={Boolean(notificationState?.[item.code]?.enabled)}
                        onChange={handleNotificationToggle(item.code)}
                      />
                      <span>
                        <span className="block text-sm font-medium text-slate-800">{notificationLabels[item.key].title}</span>
                        <span className="block text-xs text-slate-500">{notificationLabels[item.key].description}</span>
                      </span>
                    </label>
                    <select
                      className="input w-32"
                      value={notificationState?.[item.code]?.mode ?? 'immediate'}
                      onChange={(event) => handleNotificationMode(item.code, event.target.value as UserNotificationPreference['mode'])}
                    >
                      {frequencyOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              ))}
            </div>

            {notifMessage && <Alert variant="success" message={notifMessage} />}
            {notifError && <Alert variant="error" message={notifError} />}

            <div className="flex gap-3">
              <button type="submit" className="btn-primary" disabled={notifSaving}>{notifSaving ? t('common.saving') : t('common.actions.save')}</button>
              <button type="button" className="btn-secondary" onClick={handleNotificationsReset} disabled={notifSaving}>{t('common.actions.reset')}</button>
            </div>
          </form>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">{t('app.profile.sections.security.title')}</h2>
          <p className="mb-4 mt-1 text-sm text-slate-500">{t('app.profile.sections.security.description')}</p>

          <dl className="space-y-3 text-sm text-slate-700">
            <div>
              <dt className="font-medium text-slate-800">{t('app.profile.security.role')}</dt>
              <dd className="capitalize">{security?.role ?? me?.role ?? '—'}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-800">{t('app.profile.security.supervisor')}</dt>
              <dd>{supervisorName}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-800">{t('app.profile.security.companies')}</dt>
              <dd>
                {(security?.companies ?? []).length === 0 ? (
                  <span>{t('app.profile.security.companies_empty')}</span>
                ) : (
                  <ul className="space-y-1">
                    {security?.companies.map((company) => (
                      <li key={company.id} className="flex items-center gap-2">
                        <span>{company.name || company.id}</span>
                        {company.can_edit && <span className="badge text-emerald-700">{t('app.profile.security.company_edit_badge')}</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-slate-800">{t('app.profile.security.last_login')}</dt>
              <dd>{security?.last_login_at ? new Date(security.last_login_at).toLocaleString() : '—'}</dd>
            </div>
          </dl>

          <div className="mt-4 rounded border border-slate-200 p-3 text-sm">
            <p className="font-medium text-slate-800">{t('app.profile.security.password.title')}</p>
            <p className="text-xs text-slate-500">{t('app.profile.security.password.hint')}</p>

            <form className="mt-3 space-y-3" onSubmit={handlePasswordSubmit}>
              <Field label={t('app.profile.security.password.fields.current')}>
                <input type="password" className="input" value={passwordForm.current} onChange={(event) => setPasswordForm((prev) => ({ ...prev, current: event.target.value }))} autoComplete="current-password" />
              </Field>
              <Field label={t('app.profile.security.password.fields.new')}>
                <input type="password" className="input" value={passwordForm.next} onChange={(event) => setPasswordForm((prev) => ({ ...prev, next: event.target.value }))} autoComplete="new-password" />
              </Field>
              <Field label={t('app.profile.security.password.fields.confirm')}>
                <input type="password" className="input" value={passwordForm.confirm} onChange={(event) => setPasswordForm((prev) => ({ ...prev, confirm: event.target.value }))} autoComplete="new-password" />
              </Field>
              {passwordMessage && <Alert variant="success" message={passwordMessage} />}
              {passwordError && <Alert variant="error" message={passwordError} />}
              <button type="submit" className="btn-secondary" disabled={passwordSaving}>{passwordSaving ? t('app.profile.security.password.submitting') : t('app.profile.security.password.submit')}</button>
            </form>
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">{t('app.profile.sections.sessions.title')}</h2>
          <p className="mb-4 mt-1 text-sm text-slate-500">{t('app.profile.sections.sessions.description')}</p>

          <div className="mb-3 flex items-center gap-3">
            <button type="button" className="btn-secondary" onClick={() => loadSessions()} disabled={sessionsLoading}>{sessionsLoading ? t('app.profile.sessions.refreshing') : t('app.profile.sessions.refresh')}</button>
            <button type="button" className="btn-secondary" onClick={handleSessionsRevoke} disabled={sessionsLoading}>{t('app.profile.sessions.revoke')}</button>
          </div>

          <div className="space-y-3 text-sm">
            {sessions.length === 0 ? (
              <p className="text-slate-500">{t('app.profile.sessions.empty')}</p>
            ) : (
              sessions.map((session) => (
                <div key={session.id} className="rounded border border-slate-200 p-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-slate-800">{session.device_label || session.user_agent?.slice(0, 60) || t('app.profile.sessions.unknown_device')}</p>
                      <p className="text-xs text-slate-500">{t('app.profile.sessions.ip', { values: { value: session.ip_address || '—' } })}</p>
                      <p className="text-xs text-slate-500">{t('app.profile.sessions.created', { values: { value: session.created_at ? new Date(session.created_at).toLocaleString() : '—' } })}</p>
                      <p className="text-xs text-slate-500">{t('app.profile.sessions.last_seen', { values: { value: session.last_seen_at ? new Date(session.last_seen_at).toLocaleString() : '—' } })}</p>
                      {session.revoked_at && <p className="text-xs text-red-600">{t('app.profile.sessions.revoked_at', { values: { value: new Date(session.revoked_at).toLocaleString() } })}</p>}
                    </div>
                    {session.id === sessionId && <span className="badge text-brand-700">{t('app.profile.sessions.current_badge')}</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
      {children}
    </label>
  )
}

function Alert({ variant, message }: { variant: 'success' | 'error'; message: string }) {
  const styles = variant === 'success' ? 'alert-success' : 'alert-error'
  return (
    <div className={styles}>
      {message}
    </div>
  )
}
