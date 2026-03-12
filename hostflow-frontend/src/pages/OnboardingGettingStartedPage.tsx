import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconArrowRight, IconCheck, IconChecklist, IconUsers, IconUserPlus } from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { getOnboardingStatus, type OnboardingStatus } from '../api/client'

export default function OnboardingGettingStartedPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [status, setStatus] = useState<OnboardingStatus | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await getOnboardingStatus()
        if (!cancelled) setStatus(data)
      } catch {
        if (!cancelled) setStatus(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const steps = useMemo(
    () => {
      const businessType = status?.business_type ?? 'agency'
      const typeStep =
        businessType === 'employer'
          ? {
              key: 'vacancy',
              done: Boolean(status?.steps?.first_vacancy_created),
              title: t('app.onboarding.getting_started.step_employer.title', { defaultValue: 'Create first vacancy' }),
              desc: t('app.onboarding.getting_started.step_employer.desc', { defaultValue: 'Open your first position and set responsible recruiter.' }),
              href: '/app/vacancies',
            }
          : businessType === 'services'
            ? {
                key: 'first_client',
                done: Boolean(status?.steps?.first_client_created),
                title: t('app.onboarding.getting_started.step_services.title', { defaultValue: 'Create first client' }),
                desc: t('app.onboarding.getting_started.step_services.desc', { defaultValue: 'Add your first client to start service operations.' }),
                href: '/app/companies',
              }
            : {
                key: 'lead',
                done: Boolean(status?.steps?.first_lead_created),
                title: t('app.onboarding.getting_started.step_agency.title', { defaultValue: 'Add first lead' }),
                desc: t('app.onboarding.getting_started.step_agency.desc', { defaultValue: 'Capture first lead and assign source/status.' }),
                href: '/app/leads',
              }
      return [
        {
          key: 'company',
          done: Boolean(status?.steps?.company_created),
          title: t('app.onboarding.getting_started.step0.title', { defaultValue: 'Company created' }),
          desc: t('app.onboarding.getting_started.step0.desc', { defaultValue: 'Workspace company setup is complete.' }),
          href: '/app/clients',
        },
        typeStep,
        {
          key: 'action',
          done: Boolean(status?.steps?.next_action_created),
          title: t('app.onboarding.getting_started.step3.title', { defaultValue: 'Set next action' }),
          desc: t('app.onboarding.getting_started.step3.desc', { defaultValue: 'Add reminder/task so no lead is lost.' }),
          href: '/app/reminders',
        },
      ]
    },
    [status, t],
  )
  const doneCount = steps.filter((step) => step.done).length
  const totalCount = steps.length
  const completed = doneCount >= totalCount

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
          <IconChecklist size={14} stroke={1.9} />
          {t('app.onboarding.getting_started.badge', { defaultValue: 'Workspace ready' })}
        </div>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">
          {t('app.onboarding.getting_started.title', { defaultValue: 'Start working in 3 steps' })}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.onboarding.getting_started.subtitle', {
            defaultValue: 'Skip advanced settings for now. Create your first records and get value immediately.',
          })}
        </p>
        <p className="mt-2 text-xs font-medium text-brand-700">
          {t('app.onboarding.getting_started.progress', {
            defaultValue: 'Progress: {done}/{total}',
            values: { done: doneCount, total: totalCount },
          })}
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <article className={`rounded-xl border bg-white p-5 shadow-sm ${steps[0].done ? 'border-emerald-200' : 'border-slate-200'}`}>
          <div className="inline-flex rounded-lg bg-blue-50 p-2 text-blue-700">
            {steps[0].done ? <IconCheck size={18} stroke={2} className="text-emerald-700" /> : <IconUsers size={18} stroke={1.9} />}
          </div>
          <h2 className="mt-3 text-base font-semibold text-slate-900">
            {steps[0].title}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {steps[0].desc}
          </p>
          <Link to={steps[0].href} className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">
            {t('app.onboarding.getting_started.open', { defaultValue: 'Open' })}
            <IconArrowRight size={14} stroke={1.9} />
          </Link>
        </article>

        <article className={`rounded-xl border bg-white p-5 shadow-sm ${steps[1].done ? 'border-emerald-200' : 'border-slate-200'}`}>
          <div className="inline-flex rounded-lg bg-emerald-50 p-2 text-emerald-700">
            {steps[1].done ? <IconCheck size={18} stroke={2} className="text-emerald-700" /> : <IconUserPlus size={18} stroke={1.9} />}
          </div>
          <h2 className="mt-3 text-base font-semibold text-slate-900">
            {steps[1].title}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {steps[1].desc}
          </p>
          <Link to={steps[1].href} className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">
            {t('app.onboarding.getting_started.open', { defaultValue: 'Open' })}
            <IconArrowRight size={14} stroke={1.9} />
          </Link>
        </article>

        <article className={`rounded-xl border bg-white p-5 shadow-sm ${steps[2].done ? 'border-emerald-200' : 'border-slate-200'}`}>
          <div className="inline-flex rounded-lg bg-amber-50 p-2 text-amber-700">
            {steps[2].done ? <IconCheck size={18} stroke={2} className="text-emerald-700" /> : <IconChecklist size={18} stroke={1.9} />}
          </div>
          <h2 className="mt-3 text-base font-semibold text-slate-900">
            {steps[2].title}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {steps[2].desc}
          </p>
          <Link to={steps[2].href} className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">
            {t('app.onboarding.getting_started.open', { defaultValue: 'Open' })}
            <IconArrowRight size={14} stroke={1.9} />
          </Link>
        </article>
      </section>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => navigate('/app/overview', { replace: true })}
          className={`inline-flex items-center gap-1 rounded-lg px-4 py-2 text-sm font-medium text-white ${completed ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-brand-600 hover:bg-brand-700'}`}
        >
          {completed
            ? t('app.onboarding.getting_started.done', { defaultValue: 'Activation completed' })
            : t('app.onboarding.getting_started.go_dashboard', { defaultValue: 'Go to dashboard' })}
          <IconArrowRight size={14} stroke={1.9} />
        </button>
      </div>
    </div>
  )
}
