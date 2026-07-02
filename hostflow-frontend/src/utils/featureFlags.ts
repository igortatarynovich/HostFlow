/**
 * Centralized frontend feature flags.
 *
 * Source of truth for things that should be on/off depending on environment
 * or release readiness. Wire any new flag through `getFeatureFlag()`; callers
 * MUST NOT read `import.meta.env.*` directly.
 *
 * Naming convention:
 * - All flags are `VITE_FEATURE_<UPPER_SNAKE>` env vars.
 * - All flags default to `false` unless explicitly stated otherwise.
 *
 * See `docs/HOSTFLOW_AUDIT_AND_PLAN.md` Phase 2 / Phase 11 for the rationale
 * behind hiding onboarding scaffolding until production hardening completes.
 */

type FlagSpec = {
  envKey: string
  default: boolean
  description: string
}

const FLAG_REGISTRY = {
  /**
   * Phase 11 — onboarding wizard, WizardSetupRail and PostWizardWelcomePanel.
   * Off until module hardening (Phases 2-7) ships. The pages still exist in
   * routing so QA/devs can preview them, but they are not auto-exposed in the
   * AppShell or Dashboard until the product is ready to invest a brand-new
   * user's first 5 minutes.
   */
  onboardingWizard: {
    envKey: 'VITE_FEATURE_ONBOARDING_WIZARD',
    default: false,
    description:
      'Enables onboarding wizard scaffolding (WizardSetupRail in AppShell + PostWizardWelcomePanel on Dashboard).',
  },
  /**
   * Phase 2.6.G-5 Stage F — `candidate.recruiter_id` canonical on the frontend.
   *
   * When ON (the default, Stage F §5):
   *   - outgoing list filter uses `?recruiter_id=` instead of `?manager_id=`;
   *   - outgoing PATCH /candidates/{id} sends `recruiter_id` as the assignee
   *     field instead of `manager`;
   *   - display/logic helpers prefer `candidate.recruiter_id` over the
   *     legacy `candidate.manager` column (both are kept in lock-step by
   *     the backend shadow-write from Stage D).
   *
   * When OFF (rollback switch — set `VITE_FEATURE_CANDIDATE_RECRUITER_CANON=0`):
   *   - FE reverts to the pre-Stage-F behaviour (filter/PATCH use `manager`
   *     / `manager_id`, helpers read `candidate.manager` first). Safe because
   *     Stage D keeps `manager` ↔ `recruiter_id` synchronised in the DB.
   *
   * Rollback becomes impossible once Stage G lands (destructive migration
   * drops `candidates.manager`). Flip this flag default to `true` during
   * Stage F so Stage G is a no-op on the UI.
   */
  candidateRecruiterIdCanon: {
    envKey: 'VITE_FEATURE_CANDIDATE_RECRUITER_CANON',
    default: true,
    description:
      'Use `candidate.recruiter_id` as the canonical assignee field on the FE (filter, PATCH body, helpers). Rollback to `manager` by setting this OFF.',
  },
  requirementsWorkspace: {
    envKey: 'VITE_FEATURE_REQUIREMENTS_WORKSPACE',
    default: true,
    description: 'Enables full-page Candidate Requirements Workspace (`/candidates/:id/requirements`).',
  },
  dossierLegacy: {
    envKey: 'VITE_FEATURE_DOSSIER_LEGACY',
    default: false,
    description: 'Shows legacy RecruitmentDossierChecklist on candidate card rail (superseded by requirements workspace).',
  },
} satisfies Record<string, FlagSpec>

export type FeatureFlagKey = keyof typeof FLAG_REGISTRY

function readEnv(key: string): string | undefined {
  try {
    const meta = import.meta as ImportMeta & { env?: Record<string, string | undefined> }
    return meta.env?.[key]
  } catch {
    return undefined
  }
}

function parseBoolean(raw: string | undefined, fallback: boolean): boolean {
  if (raw == null) return fallback
  const normalized = raw.trim().toLowerCase()
  if (normalized === '' || normalized === 'undefined' || normalized === 'null') return fallback
  if (['1', 'true', 'yes', 'on'].includes(normalized)) return true
  if (['0', 'false', 'no', 'off'].includes(normalized)) return false
  return fallback
}

export function getFeatureFlag(key: FeatureFlagKey): boolean {
  const spec = FLAG_REGISTRY[key]
  return parseBoolean(readEnv(spec.envKey), spec.default)
}

export function isOnboardingWizardEnabled(): boolean {
  return getFeatureFlag('onboardingWizard')
}

/**
 * Phase 2.6.G-5 Stage F helper. Read this instead of
 * `getFeatureFlag('candidateRecruiterIdCanon')` directly so the call-sites
 * document their intent.
 *
 * Default ON (Stage F §5). Callers that want the Stage-D shadow-write
 * fallback should branch on the inverse of this check.
 */
export function isCandidateRecruiterIdCanonEnabled(): boolean {
  return getFeatureFlag('candidateRecruiterIdCanon')
}

export function isRequirementsWorkspaceEnabled(): boolean {
  return getFeatureFlag('requirementsWorkspace')
}

export function isDossierLegacyEnabled(): boolean {
  return getFeatureFlag('dossierLegacy')
}
