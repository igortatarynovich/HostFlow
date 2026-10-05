import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getWorkforceEmployeeOperationalProfile, type WorkforceEmployeeOperationalProfile } from '../../api/workforce'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import HrDriverOperatorSurface from '../../components/hr/HrDriverOperatorSurface'
import { PageShell } from '../../components/layout'
import { PageHeader } from '../../components/nav/PageHeader'
import { useToast } from '../../components/Toast'
import { usePermissions } from '../../hooks/usePermissions'
import { useI18n } from '../../i18n'
import {
  EntityWorkspaceCompositionHost,
  HR_EMPLOYEE_COMPOSITION_CONSUMER_ID,
  HR_EMPLOYEE_COMPOSITION_SLOTS,
  assertHrEmployeeCompositionSlots,
} from '../../platform/entity-workspace'
import { EntityWorkspaceCapabilityHost } from '../../platform/workspace-capability/EntityWorkspaceCapabilityHost'
import { HR_EMPLOYEE_ENTITY_HOST_CONTRIBUTIONS } from '../../platform/workspace-capability/hrEmployeeEntity'
import { HrEmployeeCommunicationSlot } from './HrEmployeeCommunicationSlot'
import { HrEmployeeFormsSlot } from './HrEmployeeFormsSlot'

export default function HrEmployeeDetailPage() {
  const { employeeId } = useParams<{ employeeId: string }>()
  const { t } = useI18n()
  const { can } = usePermissions()
  const { notify } = useToast()
  const [profile, setProfile] = useState<WorkforceEmployeeOperationalProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const manage = can('workforce.manage')
  const employee = profile?.employee ?? null

  const load = useCallback(async () => {
    if (!employeeId) return
    setLoading(true)
    try {
      setProfile(await getWorkforceEmployeeOperationalProfile(employeeId))
    } catch {
      setProfile(null)
      notify({
        variant: 'error',
        title: t('app.hr.employee_detail.load_error', { defaultValue: 'Could not load employee' }),
      })
    } finally {
      setLoading(false)
    }
  }, [employeeId, notify, t])

  const refreshProfile = useCallback(async () => {
    if (!employeeId) return
    try {
      setProfile(await getWorkforceEmployeeOperationalProfile(employeeId))
    } catch {
      /* timeline stays as last loaded */
    }
  }, [employeeId])

  useEffect(() => {
    if (can('workforce.view') && employeeId) void load()
  }, [can, employeeId, load])

  useEffect(() => {
    if (loading || !employee) return
    const hash = window.location.hash
    if (!hash) return
    document.querySelector(hash)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [loading, employee])

  if (!can('workforce.view')) {
    return (
      <div className="p-6 text-sm text-slate-600">
        {t('app.nav.hr.employees.forbidden', { defaultValue: 'You do not have access to the HR workspace.' })}
      </div>
    )
  }

  if (!employeeId) {
    return (
      <div className="p-6 text-sm text-slate-600">
        {t('app.hr.employee_detail.missing_id', { defaultValue: 'Missing employee id.' })}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6 text-sm text-slate-500">
        {t('common.loading', { defaultValue: 'Loading…' })}
      </div>
    )
  }

  if (!employee || !profile) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <p className="text-sm text-slate-600 mb-4">
          {t('app.hr.employee_detail.not_found', { defaultValue: 'Employee not found.' })}
        </p>
        <Link className="text-sm text-brand-600 hover:underline" to={CRM_APP_PATHS.hrEmployees}>
          {t('app.hr.employee_detail.back_list', { defaultValue: '← Back to employees' })}
        </Link>
      </div>
    )
  }

  assertHrEmployeeCompositionSlots(HR_EMPLOYEE_COMPOSITION_SLOTS)

  return (
    <PageShell
      className="hr-employee-workspace w-full min-w-0"
      data-entity-workspace-consumer={HR_EMPLOYEE_COMPOSITION_CONSUMER_ID}
    >
      <div className="w-full min-w-0">
        <div data-entity-workspace-slot="context-rail">
          <PageHeader
            breadcrumbItems={[
              { label: t('app.nav.hr.workspace.title', { defaultValue: 'HR workspace' }), to: CRM_APP_PATHS.hr },
              {
                to: CRM_APP_PATHS.hrEmployees,
                label: t('app.nav.items.hr_employees', { defaultValue: 'HR · Employees' }),
              },
              { label: employee.display_name },
            ]}
            title={employee.display_name}
            subtitle={employee.id}
            kind="browse"
          />
        </div>
        <div className="mt-6 min-w-0 space-y-4">
          <div data-entity-workspace-slot="overview" className="space-y-4">
            <HrDriverOperatorSurface employeeId={employeeId} manage={manage} />
          </div>
          <EntityWorkspaceCompositionHost
            consumerId={HR_EMPLOYEE_COMPOSITION_CONSUMER_ID}
            enabledSlots={['communication', 'forms']}
            renderers={{
              communication: () => (
                <HrEmployeeCommunicationSlot candidateId={String(employee.candidate_id || '')} />
              ),
              forms: () => <HrEmployeeFormsSlot />,
            }}
          />
          <EntityWorkspaceCapabilityHost
            entity={{ resourceType: 'workforce_employee', resourceId: employeeId }}
            contributions={HR_EMPLOYEE_ENTITY_HOST_CONTRIBUTIONS}
            onClose={() => undefined}
            onRefresh={() => void refreshProfile()}
          >
            {(placed) => <div data-host-region="platform_slot">{placed.platform_slot}</div>}
          </EntityWorkspaceCapabilityHost>
          <div data-entity-workspace-slot="timeline">
            <section className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-sm font-semibold text-slate-900">
                {t('app.entity_workspace.slot.timeline', { defaultValue: 'Timeline' })}
              </p>
              {profile.timeline.length === 0 ? (
                <p className="text-sm text-slate-600">
                  {t('app.hr.employee_operational.timeline_empty', { defaultValue: 'No timeline events.' })}
                </p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {profile.timeline.slice(0, 5).map((ev) => (
                    <li key={ev.id} className="text-slate-700">
                      <span className="font-medium text-slate-900">{ev.title}</span>
                      {ev.kind ? <span className="text-slate-500"> · {ev.kind}</span> : null}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      </div>
    </PageShell>
  )
}
