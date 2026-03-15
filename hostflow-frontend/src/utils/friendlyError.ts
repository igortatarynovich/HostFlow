export type FriendlyErrorInfo = {
  title: string
  detail?: string
  hint: string
}

function pickDetail(err: any): string | undefined {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail.trim() || undefined
  if (Array.isArray(detail)) {
    const msg = detail
      .map((item) => (typeof item?.msg === 'string' ? item.msg : ''))
      .filter(Boolean)
      .join('; ')
    return msg || undefined
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string' && detail.message.trim()) {
      return detail.message.trim()
    }
    if (typeof detail.code === 'string' && detail.code.trim()) {
      return detail.code.trim()
    }
    if (typeof detail.msg === 'string' && detail.msg.trim()) {
      return detail.msg.trim()
    }
  }
  const message = typeof err?.message === 'string' ? err.message.trim() : ''
  return message || undefined
}

export function getFriendlyErrorInfo(err: any, fallbackTitle: string): FriendlyErrorInfo {
  const status = Number(err?.response?.status || 0)
  const code = String(err?.code || '').trim().toUpperCase()
  const detail = pickDetail(err)
  const detailPayload = err?.response?.data?.detail
  const detailCode = String(
    (typeof detailPayload === 'object' && detailPayload && (detailPayload.code || detailPayload.error_code)) || detail || '',
  )
    .trim()
    .toUpperCase()
  const offline = typeof navigator !== 'undefined' && navigator?.onLine === false

  if (offline || code === 'ERR_NETWORK') {
    return {
      title: 'No internet connection',
      detail,
      hint: 'Check connection and retry.',
    }
  }

  if (code === 'ECONNABORTED') {
    return {
      title: 'Request timed out',
      detail,
      hint: 'Retry in a few seconds.',
    }
  }

  if (status === 401 || status === 403) {
    return {
      title: 'Access denied for this action',
      detail,
      hint: 'Refresh session or ask admin for permissions.',
    }
  }

  if (status === 402) {
    if (detailCode === 'OPERATING-COMPANY-LIMIT') {
      return {
        title: 'Operating company limit reached',
        detail,
        hint: 'Open Billing and add an extra operating company slot.',
      }
    }
    return {
      title: 'Payment required to continue',
      detail,
      hint: 'Open Billing and check subscription status.',
    }
  }

  if (status === 404) {
    return {
      title: 'Requested data was not found',
      detail,
      hint: 'Refresh data and retry the action.',
    }
  }

  if (status === 409) {
    return {
      title: 'Data conflict detected',
      detail,
      hint: 'Refresh page and retry.',
    }
  }

  if (status === 429) {
    return {
      title: 'Too many requests',
      detail,
      hint: 'Wait a moment and try again.',
    }
  }

  if (status >= 500) {
    return {
      title: 'Server is temporarily unavailable',
      detail,
      hint: 'Retry shortly. If problem persists, check service health.',
    }
  }

  return {
    title: fallbackTitle,
    detail,
    hint: 'Retry the action or refresh the page.',
  }
}
