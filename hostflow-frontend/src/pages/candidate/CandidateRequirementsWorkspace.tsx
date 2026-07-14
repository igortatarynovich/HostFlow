import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { api } from '../../api/client'
import type { Candidate } from '../../api/types'
import type { RequirementChecklistItem } from '../../api/candidateRequirements'
import type { OperationalRequirementRow } from '../../api/types/candidateRequirements'
import HandoffReadinessPane from '../../components/candidate/requirements/HandoffReadinessPane'
import RequirementActivityPane from '../../components/candidate/requirements/RequirementActivityPane'
import RequirementDataFieldsPane from '../../components/candidate/requirements/RequirementDataFieldsPane'
import RequirementDetailPane, { useRequirementLabelForType } from '../../components/candidate/requirements/RequirementDetailPane'
import RequirementScopedDocumentsDrawer from '../../components/candidate/requirements/RequirementScopedDocumentsDrawer'
import RequirementsWorkspaceNavList from '../../components/candidate/requirements/RequirementsWorkspaceNavList'
import RequirementsWorkspaceSummaryBar from '../../components/candidate/requirements/RequirementsWorkspaceSummaryBar'
import { resolveRequirementRowStatus } from '../../components/candidate/requirementsChecklistPresentation'
import { useToast } from '../../components/Toast'
import { useCandidateRequirementDocuments } from '../../hooks/useCandidateRequirementDocuments'
import { useCandidateRequirementsChecklist } from '../../hooks/useCandidateRequirementsChecklist'
import { useRequirementsWorkspace } from '../../hooks/useRequirementsWorkspace'
import { useI18n } from '../../i18n'
import { isRequirementsWorkspaceEnabled } from '../../utils/featureFlags'
import { workspaceTransferReportFromBundle } from '../../utils/workspaceTransferReadiness'

function candidateDisplayName(candidate: Candidate | null): string {
  if (!candidate) return ''
  const first = String(candidate.first_name || '').trim()
  const last = String(candidate.last_name || '').trim()
  return [first, last].filter(Boolean).join(' ') || String(candidate.id || '')
}

function isRequirementOpen(item: RequirementChecklistItem): boolean {
  if (item.evaluation?.status === 'not_applicable') return false
  return !item.fulfilled
}

function pickDefaultRequirementCode(
  requirements: RequirementChecklistItem[],
  operationalRequirements: OperationalRequirementRow[],
): string | null {
  const openOps = operationalRequirements.find((row) => row.status !== 'satisfied')
  if (openOps) return openOps.requirement_code
  const open = requirements.find(isRequirementOpen)
  if (open) return open.requirement_code
  const first = requirements.find((item) => resolveRequirementRowStatus(item) !== 'not_applicable')
  return first?.requirement_code ?? operationalRequirements[0]?.requirement_code ?? null
}

export default function CandidateRequirementsWorkspace() {
  const { id } = useParams<{ id: string }>()
  const { t } = useI18n()
  const { notify } = useToast()
  const candidateId = String(id || '').trim()
  const [refreshKey, setRefreshKey] = useState(0)
  const [selectedRequirementCode, setSelectedRequirementCode] = useState<string | null>(null)
  const [docsDrawerOpen, setDocsDrawerOpen] = useState(false)
  const [docsDrawerType, setDocsDrawerType] = useState<string | undefined>(undefined)
  const [candidate, setCandidate] = useState<Candidate | null>(null)

  const bumpRefresh = useCallback(() => {
    setRefreshKey((key) => key + 1)
  }, [])

  const { workspace, loading, error, reload } = useRequirementsWorkspace(candidateId, refreshKey)
  const { candidateDocuments, docsLoading } = useCandidateRequirementDocuments(candidateId, refreshKey)
  const labelForType = useRequirementLabelForType()

  const {
    actionBusy,
    selectEvidence,
    linkDocument,
    approveEvidence,
    rejectEvidence,
    replaceEvidence,
    error: actionError,
  } = useCandidateRequirementsChecklist(candidateId, refreshKey, bumpRefresh)

  const requirements = workspace?.checklist.requirements ?? []
  const operationalRequirements = workspace?.operational_requirements ?? []

  const selectedItem = useMemo(
    () => requirements.find((item) => item.requirement_code === selectedRequirementCode) ?? null,
    [requirements, selectedRequirementCode],
  )

  const selectedOperational = useMemo(
    () =>
      operationalRequirements.find((item) => item.requirement_code === selectedRequirementCode) ?? null,
    [operationalRequirements, selectedRequirementCode],
  )

  useEffect(() => {
    const total = requirements.length + operationalRequirements.length
    if (!total) {
      setSelectedRequirementCode(null)
      return
    }
    const knownCodes = new Set([
      ...requirements.map((item) => item.requirement_code),
      ...operationalRequirements.map((item) => item.requirement_code),
    ])
    if (selectedRequirementCode && knownCodes.has(selectedRequirementCode)) {
      return
    }
    setSelectedRequirementCode(pickDefaultRequirementCode(requirements, operationalRequirements))
  }, [requirements, operationalRequirements, selectedRequirementCode])

  const loadCandidate = useCallback(async () => {
    if (!candidateId) {
      setCandidate(null)
      return
    }
    try {
      const { data } = await api.get<Candidate>(`/candidates/${candidateId}`)
      setCandidate(data)
    } catch {
      setCandidate(null)
    }
  }, [candidateId])

  useEffect(() => {
    void loadCandidate()
  }, [loadCandidate])

  const openDocsDrawer = useCallback((typeCode?: string) => {
    setDocsDrawerType(typeCode)
    setDocsDrawerOpen(true)
  }, [])

  const closeDocsDrawer = useCallback(() => {
    setDocsDrawerOpen(false)
  }, [])

  const wrapAction = useCallback(
    async (fn: () => Promise<unknown>, successKey: string, defaultSuccess: string) => {
      const result = await fn()
      if (result !== null && result !== undefined) {
        notify({
          variant: 'success',
          title: t(successKey, { defaultValue: defaultSuccess }),
        })
        void reload()
      }
      return result
    },
    [notify, reload, t],
  )

  const cardPath = candidateId
    ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}`
    : CRM_APP_PATHS.candidates
  const name = candidateDisplayName(candidate)
  const canEdit = workspace?.can_edit ?? true

  if (!isRequirementsWorkspaceEnabled()) {
    return (
      <PageShell>
        <PageShellHeader>
          <PageHeader
            breadcrumbItems={[
              {
                label: t('app.nav.items.candidates', { defaultValue: 'Candidates' }),
                to: CRM_APP_PATHS.candidates,
              },
              {
                label: t('app.candidate_requirements.workspace.title', { defaultValue: 'Requirements' }),
              },
            ]}
            kind="browse"
          />
        </PageShellHeader>
        <div className="px-4 pb-4 text-sm text-slate-600">
          {t('app.candidate_requirements.workspace.disabled', {
            defaultValue: 'Requirements workspace is not enabled in this environment.',
          })}
        </div>
      </PageShell>
    )
  }

  if (!candidateId) {
    return (
      <PageShell>
        <PageShellHeader>
          <PageHeader breadcrumbCurrentLabel={t('common.errors.not_found', { defaultValue: 'Not found' })} kind="browse" />
        </PageShellHeader>
        <div className="px-4 pb-4 text-sm text-slate-600">
          {t('common.errors.not_found', { defaultValue: 'Not found' })}
        </div>
      </PageShell>
    )
  }

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          breadcrumbItems={[
            {
              label: t('app.nav.items.candidates', { defaultValue: 'Candidates' }),
              to: CRM_APP_PATHS.candidates,
            },
            ...(name ? [{ label: name, to: cardPath }] : []),
            {
              label: t('app.candidate_requirements.workspace.title', { defaultValue: 'Requirements' }),
            },
          ]}
          subtitle={t('app.candidate_requirements.workspace.subtitle', {
            defaultValue: 'Close each requirement before handoff to HR.',
          })}
          kind="browse"
          secondaryActions={
            <button
              type="button"
              className="btn btn-sm rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              onClick={() => void reload()}
              disabled={loading}
            >
              {t('common.actions.refresh', { defaultValue: 'Refresh' })}
            </button>
          }
        />
      </PageShellHeader>

      <div className="mx-auto flex min-h-0 w-full max-w-6xl flex-1 flex-col gap-4 overflow-y-auto px-4 pb-10 sm:pb-6">

      {loading && !workspace ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          {t('common.loading', { defaultValue: 'Loading…' })}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
          <p>{error}</p>
          <button
            type="button"
            className="mt-2 text-xs font-semibold text-rose-800 underline"
            onClick={() => void reload()}
          >
            {t('common.retry', { defaultValue: 'Retry' })}
          </button>
        </div>
      ) : null}

      {actionError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900">{actionError}</div>
      ) : null}

      {workspace ? (
        <>
          <RequirementsWorkspaceSummaryBar
            summary={workspace.summary}
            transferReadiness={workspace.transfer_readiness}
            canEdit={workspace.can_edit}
          />

          <RequirementDataFieldsPane
            candidate={candidate}
            fieldRequirements={workspace.field_requirements.required_fields}
            canEdit={canEdit}
            onSaved={(updated) => {
              setCandidate(updated)
              bumpRefresh()
            }}
          />

          <div className="grid gap-4 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)] lg:items-start">
            <RequirementsWorkspaceNavList
              requirements={requirements}
              fieldRequirements={workspace.field_requirements.required_fields}
              operationalRequirements={operationalRequirements}
              selectedRequirementCode={selectedRequirementCode}
              onSelectRequirement={setSelectedRequirementCode}
            />

            <div className="min-w-0">
              {selectedOperational ? (
                <RequirementActivityPane
                  candidateId={candidateId}
                  item={selectedOperational}
                  canEdit={canEdit}
                  onCompleted={() => {
                    bumpRefresh()
                    void reload()
                  }}
                />
              ) : selectedItem ? (
                <RequirementDetailPane
                  key={selectedItem.requirement_code}
                  item={selectedItem}
                  canEdit={canEdit}
                  actionBusy={actionBusy}
                  labelForType={labelForType}
                  candidateDocuments={candidateDocuments}
                  docsLoading={docsLoading}
                  layout="workspace"
                  onSelectVariant={(variantCode) =>
                    wrapAction(
                      () => selectEvidence(selectedItem.requirement_code, variantCode),
                      'app.candidate_card.requirements_checklist.toast_selected',
                      'Evidence selected',
                    )
                  }
                  onLinkDocument={(evidenceId, documentId) =>
                    wrapAction(
                      () => linkDocument(evidenceId, documentId),
                      'app.candidate_card.requirements_checklist.toast_linked',
                      'Document linked',
                    )
                  }
                  onApprove={(evidenceId) =>
                    wrapAction(
                      () => approveEvidence(evidenceId),
                      'app.candidate_card.requirements_checklist.toast_approved',
                      'Requirement approved',
                    )
                  }
                  onReject={(evidenceId, reason) =>
                    wrapAction(
                      () => rejectEvidence(evidenceId, reason),
                      'app.candidate_card.requirements_checklist.toast_rejected',
                      'Evidence rejected',
                    )
                  }
                  onReplace={(variantCode) =>
                    wrapAction(
                      () => replaceEvidence(selectedItem.requirement_code, variantCode),
                      'app.candidate_card.requirements_checklist.toast_replaced',
                      'Evidence replaced',
                    )
                  }
                  onOpenDocs={openDocsDrawer}
                  onUpload={() => openDocsDrawer(undefined)}
                />
              ) : (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
                  {t('app.candidate_requirements.workspace.select_requirement', {
                    defaultValue: 'Select a requirement from the list to review and confirm evidence.',
                  })}
                </div>
              )}
            </div>
          </div>

          <p className="text-xs text-slate-500">
            {t('app.candidate_requirements.workspace.profile_hint', {
              defaultValue: 'Profile: {profile}',
              profile: workspace.entity_profile_code || '—',
            })}
          </p>

          <HandoffReadinessPane
            candidateId={candidateId}
            refreshTrigger={refreshKey}
            canEdit={canEdit}
            transferReport={workspace ? workspaceTransferReportFromBundle(workspace) : null}
            transferReportLoading={loading}
          />
        </>
      ) : null}

      <RequirementScopedDocumentsDrawer
        open={docsDrawerOpen}
        candidateId={candidateId}
        initialType={docsDrawerType}
        onClose={closeDocsDrawer}
        onDocumentsChanged={bumpRefresh}
      />
      </div>
    </PageShell>
  )
}
