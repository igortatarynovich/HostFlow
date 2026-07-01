/** Targets `MetaLeadsAdminPage` main tabs (post–simple-UX refactor). */
export type LeadErrorSuggestionTab = 'advanced' | 'processing' | 'field_mapping'

export type LeadErrorSuggestion = {
  tab: LeadErrorSuggestionTab
  hint: string
  actionLabel: string
}

/**
 * Convert lead.error diagnostic code into a UX-ready hint + where to go next.
 *
 * Notes:
 * - `lead.error` may include additional details after the code, so we match by prefix.
 * - i18n translations are provided by the caller (via `t`).
 */
export function getLeadErrorSuggestion(error: string | null | undefined, t: any): LeadErrorSuggestion | null {
  const code = (error ?? '').trim()
  if (!code) return null

  if (code.startsWith('GRAPH_NO_TOKEN')) {
    return {
      tab: 'advanced',
      hint: t('admin.meta_leads.logs.suggestions.graph_no_token.hint', {
        defaultValue: 'Нет Graph access token для page_id. Обновите Credentials и повторите.',
      }),
      actionLabel: t('admin.meta_leads.logs.suggestions.graph_no_token.action', { defaultValue: 'Advanced' }),
    }
  }

  if (code.startsWith('VACANCY_NOT_RESOLVED')) {
    return {
      tab: 'advanced',
      hint: t('admin.meta_leads.logs.suggestions.vacancy_not_resolved.hint', {
        defaultValue: 'Вакансия не найдена. Проверьте “Mapping объявлений” (ad_id → vacancy_id).',
      }),
      actionLabel: t('admin.meta_leads.logs.suggestions.vacancy_not_resolved.action', { defaultValue: 'Advanced' }),
    }
  }

  if (code.startsWith('NO_CONTACTS')) {
    return {
      tab: 'field_mapping',
      hint: t('admin.meta_leads.logs.suggestions.no_contacts.hint', {
        defaultValue: 'Meta не прислал email/phone по вашему маппингу. Проверьте Field mapping и Retry.',
      }),
      actionLabel: t('admin.meta_leads.logs.suggestions.no_contacts.action', { defaultValue: 'Field mapping' }),
    }
  }

  if (code.startsWith('COMPANY_NOT_RESOLVED') || code.startsWith('OWN_COMPANY_REQUIRED')) {
    return {
      tab: 'processing',
      hint: t('admin.meta_leads.logs.suggestions.company_not_resolved.hint', {
        defaultValue: 'Не удалось определить компанию. Проверьте “Компания по умолчанию” и логіку маппинга.',
      }),
      actionLabel: t('admin.meta_leads.logs.suggestions.company_not_resolved.action', { defaultValue: 'Processing' }),
    }
  }

  return {
    tab: 'processing',
    hint: t('admin.meta_leads.logs.suggestions.generic.hint', {
      defaultValue: 'Посмотрите настройки и попробуйте Retry (или Reroute).',
    }),
    actionLabel: t('admin.meta_leads.logs.suggestions.generic.action', { defaultValue: 'Processing' }),
  }
}

