export type SalesInquiryTimelineItem = {
  at: string
  kind: string
  source: string
  title?: string | null
  description?: string | null
}

const RECRUITMENT_COMM_TITLE = /^lead\.communication\./
const ANALYTICS_TITLE = /^analytics\./
const RECRUITMENT_NBA_TITLE = /^lead:\s*create next action/i

export function isSalesInquiryTimelineItemVisible(item: SalesInquiryTimelineItem): boolean {
  const kind = String(item.kind || '').trim()
  const title = String(item.title || '').trim()
  if (kind === 'next_action_warning' || kind === 'analytics') return false
  if (RECRUITMENT_COMM_TITLE.test(title)) return false
  if (ANALYTICS_TITLE.test(title)) return false
  if (RECRUITMENT_NBA_TITLE.test(title)) return false
  return true
}

export function salesInquiryTimelineKindTitle(
  t: (key: string, opts?: { defaultValue?: string }) => string,
  kind: string,
  title: string | null | undefined,
): string {
  const key = String(kind || '').trim()
  const mapped: Record<string, { i18n: string; fallback: string }> = {
    lead_received: { i18n: 'app.leads.detail.timeline_kinds.lead_received', fallback: 'Inquiry received' },
    call_result: { i18n: 'app.leads.detail.timeline_kinds.call_result', fallback: 'Call result' },
    stage_changed: { i18n: 'app.leads.detail.timeline_kinds.stage_changed', fallback: 'Stage changed' },
    questionnaire_email: {
      i18n: 'app.leads.detail.timeline_kinds.questionnaire_email',
      fallback: 'Questionnaire sent',
    },
    questionnaire_submitted: {
      i18n: 'app.leads.detail.timeline_kinds.questionnaire_submitted',
      fallback: 'Questionnaire received',
    },
    gdpr_notice: { i18n: 'app.leads.detail.timeline_kinds.gdpr_notice', fallback: 'GDPR notice sent' },
    gdpr_notice_failed: {
      i18n: 'app.leads.detail.timeline_kinds.gdpr_notice_failed',
      fallback: 'GDPR notice failed',
    },
  }
  const hit = mapped[key]
  if (hit) return t(hit.i18n, { defaultValue: hit.fallback })

  const raw = String(title || '').trim()
  if (raw === 'lead.received' || raw === 'lead.created' || raw === 'lead.ingested' || raw === 'lead.imported') {
    return t('app.leads.detail.timeline_kinds.lead_received', { defaultValue: 'Inquiry received' })
  }
  if (raw === 'rodo_sent' || raw === 'gdpr_notice') {
    return t('app.leads.detail.timeline_kinds.gdpr_notice', { defaultValue: 'GDPR notice sent' })
  }
  if (raw === 'rodo_sent_failed' || raw === 'gdpr_notice_failed') {
    return t('app.leads.detail.timeline_kinds.gdpr_notice_failed', { defaultValue: 'GDPR notice failed' })
  }
  if (looksLikeRawEventKey(raw) || looksLikeRawEventKey(key)) {
    return t('app.leads.detail.timeline_kinds.system_event', { defaultValue: 'System event' })
  }
  return raw || key || '—'
}

export function salesInquiryTimelineDescription(
  t: (key: string, opts?: { defaultValue?: string }) => string,
  item: SalesInquiryTimelineItem,
): string | null {
  const raw = String(item.description || '').trim()
  if (!raw) return null
  if (item.kind === 'call_result') {
    const [code, ...rest] = raw.split(' — ')
    const label = t(`app.leads.detail.call_result.results.${code}`, { defaultValue: code })
    return rest.length ? `${label} — ${rest.join(' — ')}` : label
  }
  return raw
}

function looksLikeRawEventKey(value: string): boolean {
  const v = value.trim()
  if (!v) return false
  if (v.includes('.')) return /^[a-z][a-z0-9_.]+$/i.test(v)
  return /^[a-z]+_[a-z0-9_]+$/i.test(v)
}
