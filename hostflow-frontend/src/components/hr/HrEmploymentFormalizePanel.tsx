/**
 * ESO-4: Formalize on the HR handoff case.
 * Context-required formal actions only → ready_to_create_employee.
 * No Employee mint, Started CTA, HR-card create, or runtime pathway/rates menus.
 */
import { useMemo } from 'react'
import { useI18n } from '../../i18n'
import type { EmploymentFormalizeOut } from '../../api/hrWorkspace'
import {
  buildFormalizePatchForPrimary,
  formalizeSurfaceMode,
  isFormalizeTerminalAllowCreate,
  operatorCanConfirmCurrentFormalItem,
  primaryFormalItem,
  shouldShowFormalizeRuntimeChoice,
} from '../../utils/employmentFormalizeUi'

type Props = {
  formalize: EmploymentFormalizeOut | null
  evaluating?: boolean
  confirming?: boolean
  error?: string | null
  onConfirm: (patch: { confirmed_actions: string[] }) => void
}

export default function HrEmploymentFormalizePanel({
  formalize,
  evaluating,
  confirming,
  error,
  onConfirm,
}: Props) {
  const { t } = useI18n()
  const { mode, readyToCreateEmployee } = useMemo(
    () => formalizeSurfaceMode(formalize),
    [formalize],
  )
  const primary = useMemo(() => primaryFormalItem(formalize), [formalize])
  const canConfirm = operatorCanConfirmCurrentFormalItem(formalize)
  const terminal = isFormalizeTerminalAllowCreate(formalize)
  const primaryCode = String(primary?.code || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')

  if (evaluating && !formalize) {
    return (
      <section
        id="hr-employment-formalize"
        className="scroll-mt-24 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
        data-testid="hr-employment-formalize-evaluating"
      >
        {t('app.hr.employment_formalize.evaluating', {
          defaultValue: 'Evaluating formalization…',
        })}
      </section>
    )
  }

  if (!formalize) return null

  const blockerMessage =
    error ||
    formalize.rejection_reason ||
    (Array.isArray(formalize.blockers) && formalize.blockers[0]
      ? String(
          (formalize.blockers[0] as { message?: string }).message ||
            (formalize.blockers[0] as { code?: string }).code ||
            '',
        )
      : '') ||
    primary?.message ||
    ''

  const submitConfirm = () => {
    if (!primary?.code) return
    const patch = buildFormalizePatchForPrimary(primary.code)
    if (!patch) return
    onConfirm(patch)
  }

  return (
    <section
      id="hr-employment-formalize"
      className="scroll-mt-24 space-y-3 rounded-lg border border-slate-200 bg-white px-4 py-4"
      data-testid="hr-employment-formalize-panel"
      data-decision={mode}
      data-ready-to-create-employee={readyToCreateEmployee ? 'true' : 'false'}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.hr.employment_formalize.title', { defaultValue: 'Formalize employment' })}
        </h2>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
          {mode}
        </span>
      </div>

      {/* Zero-choice proof: pathway / person / vacancy / rates menus are forbidden. */}
      <div data-testid="hr-employment-formalize-zero-choice" hidden aria-hidden="true" />
      {shouldShowFormalizeRuntimeChoice('pathway') ||
      shouldShowFormalizeRuntimeChoice('rates') ||
      shouldShowFormalizeRuntimeChoice('contract_subtype') ||
      shouldShowFormalizeRuntimeChoice('position') ? (
        <select data-testid="hr-employment-formalize-runtime-choice" aria-label="forbidden">
          <option>forbidden</option>
        </select>
      ) : null}

      {mode === 'missing' ? (
        <div
          className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950"
          data-testid="hr-employment-formalize-missing"
        >
          <p className="font-medium">
            {t('app.hr.employment_formalize.missing_title', {
              defaultValue: 'One formal action is required',
            })}
          </p>
          <p className="mt-1" data-testid="hr-employment-formalize-primary">
            {primary?.message || primary?.code || blockerMessage}
          </p>

          {canConfirm && primaryCode === 'confirm_employment_contract_basis' ? (
            <div className="mt-3">
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={confirming}
                onClick={submitConfirm}
                data-testid="hr-employment-formalize-confirm"
              >
                {t('app.hr.employment_formalize.confirm_contract_basis', {
                  defaultValue: 'Confirm contract basis',
                })}
              </button>
            </div>
          ) : null}

          {canConfirm && primaryCode === 'work_authorization_evidence' ? (
            <div className="mt-3">
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={confirming}
                onClick={submitConfirm}
                data-testid="hr-employment-formalize-confirm"
              >
                {t('app.hr.employment_formalize.confirm_work_auth', {
                  defaultValue: 'Confirm work authorization on file',
                })}
              </button>
            </div>
          ) : null}

          <p className="mt-2 text-xs text-amber-900/80">
            {t('app.hr.employment_formalize.context_only', {
              defaultValue:
                'Only context-required formal items appear here — known evidence is not re-asked.',
            })}
          </p>
        </div>
      ) : null}

      {terminal ? (
        <div
          className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
          data-testid="hr-employment-formalize-complete"
        >
          <p className="font-medium">
            {t('app.hr.employment_formalize.complete_title', {
              defaultValue: 'Formalization complete',
            })}
          </p>
          <p className="mt-1" data-testid="hr-employment-formalize-ready-create">
            {t('app.hr.employment_formalize.ready_to_create_employee', {
              defaultValue: 'ready_to_create_employee=true — Employee creation is allowed.',
            })}
          </p>
          <p
            className="mt-2 text-xs text-emerald-800/80"
            data-testid="hr-employment-formalize-no-employee-mint"
          >
            {t('app.hr.employment_formalize.no_employee_mint', {
              defaultValue:
                'Employee is not created in this step. Started and HR-card create stay closed.',
            })}
          </p>
          {/* Terminal guard: no Create Employee / Started / HR-card CTAs. */}
          <div data-testid="hr-employment-formalize-no-create-cta" hidden aria-hidden="true" />
          <div data-testid="hr-employment-formalize-no-started" hidden aria-hidden="true" />
        </div>
      ) : null}

      {mode === 'blocked' || mode === 'rejected' ? (
        <div
          className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-950"
          data-testid="hr-employment-formalize-blocked"
        >
          <p className="font-medium">
            {t('app.hr.employment_formalize.blocked_title', {
              defaultValue: 'Formalize blocked',
            })}
          </p>
          <p className="mt-1" data-testid="hr-employment-formalize-blocker">
            {blockerMessage ||
              t('app.hr.employment_formalize.blocked_fallback', {
                defaultValue: 'Resolve employable / ready_to_formalize preconditions first.',
              })}
          </p>
          <p className="mt-2 text-xs text-rose-900/80" data-testid="hr-employment-formalize-no-fake-action">
            {t('app.hr.employment_formalize.no_fake_action', {
              defaultValue: 'No Formalize shortcut when preconditions fail.',
            })}
          </p>
        </div>
      ) : null}

      {formalize.pathway_id ? (
        <p className="text-xs text-slate-500" data-testid="hr-employment-formalize-pathway">
          {t('app.hr.employment_formalize.pathway_set', {
            defaultValue: 'Legal pathway (system): {id}',
            id: formalize.pathway_id,
          })}
        </p>
      ) : null}
    </section>
  )
}
