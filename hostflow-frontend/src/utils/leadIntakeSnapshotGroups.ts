import type { Lead } from '../api/types'
import { formatLeadPipelineError } from './leadPipelineErrors'
import { formatQualificationReasonLabel, readLeadQualificationPreview } from './leadQualificationPreview'

/** Visual urgency for scan → decide (not decorative). */
export type IntakeSignalSeverity = 'critical' | 'risk' | 'positive' | 'duplicate' | 'info'

export type IntakeSnapshotSignal = { key: string; severity: IntakeSignalSeverity; label: string }

export type IntakeSnapshotGroupId = 'driving' | 'communication' | 'legal'

export type IntakeSnapshotGroup = {
  id: IntakeSnapshotGroupId
  titleKey: string
  signals: IntakeSnapshotSignal[]
}

type TFn = (key: string, opts?: { defaultValue?: string; values?: Record<string, string | number> }) => string

function str(v: unknown): string | null {
  if (v == null) return null
  const s = String(v).trim()
  return s || null
}

function listStr(v: unknown): string | null {
  if (Array.isArray(v)) {
    const xs = v.map((x) => String(x).trim()).filter(Boolean)
    return xs.length ? xs.join(', ') : null
  }
  return str(v)
}

function documentsBlob(n: Record<string, unknown>): string {
  const raw = listStr(n.documents)
  return raw ? raw.toLowerCase() : ''
}

/** Heuristic flags from free-text / checklist-style document fields. */
function sniffDrivingCerts(blob: string): { code95: boolean; tachograph: boolean } {
  if (!blob.trim()) return { code95: false, tachograph: false }
  const code95 =
    /\bcode\s*95\b/i.test(blob) ||
    /\bc\s*\+\s*e\b/i.test(blob) ||
    blob.includes('code95') ||
    blob.includes('c+e') ||
    /\bcee\b/i.test(blob)
  const tachograph =
    /\btachograph\b/i.test(blob) || /\bchip\s*card\b/i.test(blob) || /\bdriver\s*card\b/i.test(blob) || /\btacho\b/i.test(blob)
  return { code95, tachograph }
}

function fitReasonSeverity(code: string): IntakeSignalSeverity {
  const c = code.trim().toLowerCase()
  if (c.includes('no_match') || c.includes('reject') || c.includes('hard')) return 'critical'
  return 'risk'
}

export function buildIntakeSnapshotGroups(lead: Lead, normalized: Record<string, unknown>, t: TFn): IntakeSnapshotGroup[] {
  const driving: IntakeSnapshotSignal[] = []
  const communication: IntakeSnapshotSignal[] = []
  const legal: IntakeSnapshotSignal[] = []

  const st = String(lead.status || '')
    .trim()
    .toLowerCase()
  if (st === 'duplicate_review') {
    legal.push({
      key: 'dup_review',
      severity: 'duplicate',
      label: t('app.leads.intake_workspace.snapshot.duplicate_review_active'),
    })
  }

  if (typeof normalized.in_poland === 'boolean') {
    driving.push({
      key: 'pl',
      severity: 'info',
      label: normalized.in_poland ? t('app.leads.intake_workspace.snapshot.in_poland_yes') : t('app.leads.intake_workspace.snapshot.in_poland_no'),
    })
  } else if (str(normalized.country) || str(normalized.geo_country)) {
    driving.push({
      key: 'geo',
      severity: 'info',
      label: t('app.leads.intake_workspace.snapshot.country', {
        values: { value: str(normalized.country) || str(normalized.geo_country) || '—' },
      }),
    })
  }

  const eu = normalized.experience_eu_years
  if (typeof eu === 'number') {
    driving.push({
      key: 'exp',
      severity: eu > 0 ? 'positive' : 'risk',
      label: eu > 0 ? t('app.leads.intake_workspace.snapshot.exp_years', { values: { n: eu } }) : t('app.leads.intake_workspace.snapshot.exp_none'),
    })
  }

  const docsDisplay = listStr(normalized.documents)
  const blob = documentsBlob(normalized)
  const certs = sniffDrivingCerts(blob)

  if (docsDisplay) {
    driving.push(
      certs.code95
        ? { key: 'code95_ok', severity: 'positive', label: t('app.leads.intake_workspace.snapshot.code95_present') }
        : { key: 'code95_no', severity: 'risk', label: t('app.leads.intake_workspace.snapshot.code95_missing') },
    )
    driving.push(
      certs.tachograph
        ? { key: 'tacho_ok', severity: 'positive', label: t('app.leads.intake_workspace.snapshot.tachograph_present') }
        : { key: 'tacho_no', severity: 'risk', label: t('app.leads.intake_workspace.snapshot.tachograph_missing') },
    )
    driving.push({
      key: 'docs',
      severity: 'positive',
      label: t('app.leads.intake_workspace.snapshot.docs_list', {
        values: { list: docsDisplay.length > 80 ? `${docsDisplay.slice(0, 77)}…` : docsDisplay },
      }),
    })
  } else {
    driving.push({ key: 'docs_missing', severity: 'risk', label: t('app.leads.intake_workspace.snapshot.docs_missing') })
  }

  const langs = listStr(normalized.languages) || str(normalized.language)
  if (langs) {
    communication.push({
      key: 'lang',
      severity: 'info',
      label: t('app.leads.intake_workspace.snapshot.languages', { values: { list: langs } }),
    })
  }

  const phone = str(normalized.phone)
  communication.push({
    key: 'phone',
    severity: phone ? 'positive' : 'critical',
    label: phone ? t('app.leads.intake_workspace.snapshot.phone_ok') : t('app.leads.intake_workspace.snapshot.phone_missing'),
  })

  const email = str(normalized.email)
  if (email) {
    communication.push({ key: 'email', severity: 'info', label: t('app.leads.intake_workspace.snapshot.email', { values: { email } }) })
  }

  const preferredContact = str(normalized.preferred_contact) || str(normalized.preferred_contact_raw)
  if (preferredContact) {
    const channelKey = `app.candidate_card.contacts.options.${preferredContact}`
    const channelLabel = t(channelKey)
    communication.push({
      key: 'preferred_contact',
      severity: 'info',
      label: t('app.leads.intake_workspace.snapshot.preferred_contact', {
        values: { value: channelLabel === channelKey ? preferredContact : channelLabel },
      }),
    })
  }

  const polandBasis = str(normalized.poland_stay_basis) || str(normalized.poland_stay_basis_raw)
  if (polandBasis) {
    const basisKey = `app.candidate_card.status.poland_basis.${polandBasis}`
    const basisLabel = t(basisKey)
    legal.push({
      key: 'poland_basis',
      severity: 'info',
      label: t('app.leads.intake_workspace.snapshot.poland_stay', {
        values: { value: basisLabel === basisKey ? polandBasis : basisLabel },
      }),
    })
  }

  const citizenship = str(normalized.nationality) || str(normalized.nationality_code) || str(normalized.country) || str(normalized.geo_country)
  if (citizenship) {
    legal.push({
      key: 'citizenship',
      severity: 'info',
      label: t('app.leads.intake_workspace.snapshot.citizenship_line', { values: { value: citizenship } }),
    })
  }

  const err = lead.error?.trim()
  if (err === 'LEAD_FIT_NO_MATCH') {
    legal.push({
      key: 'fit_pipe',
      severity: 'critical',
      label: formatLeadPipelineError(err, t),
    })
  } else if (err === 'LEAD_FIT_NEEDS_INFO') {
    legal.push({
      key: 'fit_pipe',
      severity: 'risk',
      label: formatLeadPipelineError(err, t),
    })
  }

  const preview = readLeadQualificationPreview(lead.normalized)
  if (preview?.fit_reasons?.length) {
    for (const r of preview.fit_reasons.slice(0, 3)) {
      legal.push({
        key: `fit_${r}`,
        severity: fitReasonSeverity(String(r)),
        label: formatQualificationReasonLabel(r, t),
      })
    }
  }

  const groups: IntakeSnapshotGroup[] = []
  if (driving.length) {
    groups.push({ id: 'driving', titleKey: 'app.leads.intake_workspace.snapshot.group_driving', signals: driving })
  }
  if (communication.length) {
    groups.push({ id: 'communication', titleKey: 'app.leads.intake_workspace.snapshot.group_communication', signals: communication })
  }
  if (legal.length) {
    groups.push({ id: 'legal', titleKey: 'app.leads.intake_workspace.snapshot.group_legal', signals: legal })
  }

  return groups
}

/** One-line summary for decision rail “Review fit” step. */
export function intakeFitReviewSummary(lead: Lead, t: TFn): string | null {
  const err = lead.error?.trim()
  if (err === 'LEAD_FIT_NO_MATCH' || err === 'LEAD_FIT_NEEDS_INFO') {
    return formatLeadPipelineError(err, t)
  }
  const preview = readLeadQualificationPreview(lead.normalized)
  const fs = preview?.fit_status?.trim()
  if (fs) {
    const k = `app.leads.qualification.fit_status.${fs}`
    const tr = t(k)
    return tr === k ? fs : tr
  }
  return null
}
