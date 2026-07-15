import { api } from './client'

export const SETUP_READINESS_SCOPE = 'recruitment.setup.intake' as const

export type SetupGateId = 'G0' | 'G1' | 'G2' | 'G3' | 'G4' | 'G5' | 'G6' | 'G7' | 'G8'

export type SetupGateStatus = 'pass' | 'fail' | 'not_applicable'

export type SetupReadinessGate = {
  id: SetupGateId
  status: SetupGateStatus
  applicable: boolean
  blocker_text?: string | null
}

export type SetupReadinessNextAction = {
  gate_id: SetupGateId
  label_key: string
  handler_ref: string
}

export type SetupReadinessSnapshot = {
  scope: typeof SETUP_READINESS_SCOPE | string
  ready: boolean
  business_type: 'agency' | 'employer' | 'services'
  gates: SetupReadinessGate[]
  blockers: string[]
  next_action: SetupReadinessNextAction | null
}

export async function getSetupReadiness(): Promise<SetupReadinessSnapshot> {
  const { data } = await api.get<SetupReadinessSnapshot>('/onboarding/setup-readiness')
  return data
}

export type CandidateIntakeManualResult = {
  manual_intake_declared: boolean
  setup_ready: boolean
}

export async function declareManualCandidateIntake(): Promise<CandidateIntakeManualResult> {
  const { data } = await api.post<CandidateIntakeManualResult>('/onboarding/setup/candidate-intake/manual')
  return data
}
