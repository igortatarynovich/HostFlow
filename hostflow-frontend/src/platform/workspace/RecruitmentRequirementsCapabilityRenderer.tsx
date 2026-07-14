import { useEffect, useMemo, useState, type ReactNode } from 'react'
import type { RequirementsWorkspaceResponse } from '../../api/candidateRequirements'
import { usePermissions } from '../../hooks/usePermissions'
import { useI18n } from '../../i18n'
import { RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY } from '@hostflow/workspace'
import WorkspaceStatusRail from './WorkspaceStatusRail'
import {
  aggregateRecruitmentRequirementsStatus,
  buildCandidateRecruitmentSession,
  getWorkspaceSectionRegistry,
} from './recruitmentWorkspaceStatus'
import { workspacePermissionsFromCan, workspaceSectionAllowed } from './permissionsBridge'

type Props = {
  candidateId: string
  tenantId: string
  workspace: RequirementsWorkspaceResponse | null
  workspaceLoading: boolean
  children: ReactNode
}

/**
 * Step 5 capability renderer: recruitment.requirements
 * Composes registry + readiness aggregation + status rail; body stays module UI (children).
 */
export default function RecruitmentRequirementsCapabilityRenderer({
  candidateId,
  tenantId,
  workspace,
  workspaceLoading,
  children,
}: Props) {
  const { t } = useI18n()
  const { can, tenantId: authTenantId } = usePermissions()
  const [statusLoading, setStatusLoading] = useState(false)
  const [statusSnapshot, setStatusSnapshot] = useState<Awaited<
    ReturnType<typeof aggregateRecruitmentRequirementsStatus>
  > | null>(null)

  const session = useMemo(
    () => buildCandidateRecruitmentSession(candidateId, tenantId || authTenantId),
    [candidateId, tenantId, authTenantId],
  )

  const userPermissions = useMemo(() => workspacePermissionsFromCan(can), [can])

  const sectionVisible = useMemo(() => {
    const registry = getWorkspaceSectionRegistry()
    const sections = registry.listSections(session, userPermissions)
    return sections.some((s) => s.capability_key === RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY)
  }, [session, userPermissions])

  useEffect(() => {
    if (!workspace || !sectionVisible) {
      setStatusSnapshot(null)
      return
    }
    let cancelled = false
    setStatusLoading(true)
    void aggregateRecruitmentRequirementsStatus(workspace, session, userPermissions)
      .then((snapshot) => {
        if (!cancelled) setStatusSnapshot(snapshot)
      })
      .finally(() => {
        if (!cancelled) setStatusLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [workspace, session, userPermissions, sectionVisible])

  if (!workspaceSectionAllowed(['candidates.view'], can)) {
    return (
      <div className="mx-auto max-w-4xl p-6 text-sm text-slate-600" data-testid="workspace-section-denied">
        {t('workspace.section.access_denied', {
          defaultValue: 'You do not have permission to open this workspace section.',
        })}
      </div>
    )
  }

  if (!sectionVisible) {
    return (
      <div className="mx-auto max-w-4xl p-6 text-sm text-slate-600" data-testid="workspace-section-hidden">
        {t('workspace.section.not_available', {
          defaultValue: 'This workspace section is not available.',
        })}
      </div>
    )
  }

  return (
    <div
      className="flex flex-col gap-4"
      data-workspace-capability={RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY}
      data-workspace-context={session.context}
    >
      <WorkspaceStatusRail
        snapshot={statusSnapshot}
        loading={workspaceLoading || statusLoading}
      />
      {children}
    </div>
  )
}
