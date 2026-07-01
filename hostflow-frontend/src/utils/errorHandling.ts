/**
 * Centralized error handling utilities
 * Provides consistent error message extraction and formatting across the application
 */

export interface ErrorInfo {
  message: string
  messages: string[]
  statusCode?: number
  isNetworkError: boolean
  isNotFound: boolean
  isValidationError: boolean
  rawError: unknown
}

/**
 * Extracts user-friendly error messages from various error formats
 */
export function extractErrorMessages(error: unknown): string[] {
  if (!error) {
    return ['Unknown error']
  }

  // Handle string errors
  if (typeof error === 'string') {
    return [error]
  }

  // Handle Error objects
  if (error instanceof Error) {
    return [error.message || 'An error occurred']
  }

  // Handle Axios/Fetch API errors
  const axiosError = error as any
  const response = axiosError?.response
  const data = response?.data

  // Network errors (no response)
  if (!response) {
    return [axiosError?.message || 'Network error. Please check your connection.']
  }

  // Extract detail from response
  const detail = data?.detail ?? data?.message ?? data?.error

  if (!detail) {
    // Fallback to status text or status code
    const statusText = response?.statusText
    const status = response?.status
    if (statusText) {
      return [statusText]
    }
    if (status) {
      return [`HTTP ${status} error`]
    }
    return ['An error occurred']
  }

  // Handle array of validation errors
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item) return null
        if (typeof item === 'string') return item
        if (typeof item === 'object') {
          const field = item.field || item.path || item.loc?.join?.('.')
          const msg = item.msg || item.message || item.error
          return field && msg ? `${field}: ${msg}` : String(msg ?? item)
        }
        return String(item)
      })
      .filter((msg): msg is string => Boolean(msg))
  }

  // Handle object errors
  if (typeof detail === 'object') {
    const msg = detail.msg || detail.message || detail.error
    if (msg) return [String(msg)]
    return [JSON.stringify(detail)]
  }

  // Handle string detail
  if (typeof detail === 'string') {
    return [detail]
  }

  return [String(detail)]
}

/**
 * Gets the primary error message (first message from extractErrorMessages)
 */
export function getErrorMessage(error: unknown, fallback: string = 'An error occurred'): string {
  const messages = extractErrorMessages(error)
  return messages[0] || fallback
}

/**
 * Extracts comprehensive error information
 */
export function getErrorInfo(error: unknown): ErrorInfo {
  const messages = extractErrorMessages(error)
  const axiosError = error as any
  const response = axiosError?.response
  const statusCode = response?.status

  return {
    message: messages[0] || 'An error occurred',
    messages,
    statusCode,
    isNetworkError: !response && Boolean(axiosError?.message),
    isNotFound: statusCode === 404,
    isValidationError: statusCode === 422 || statusCode === 400,
    rawError: error,
  }
}

/**
 * Checks if error is a network error (no response)
 */
export function isNetworkError(error: unknown): boolean {
  const axiosError = error as any
  return !axiosError?.response && Boolean(axiosError?.message)
}

/**
 * Checks if error is a validation error (400 or 422)
 */
export function isValidationError(error: unknown): boolean {
  const axiosError = error as any
  const status = axiosError?.response?.status
  return status === 400 || status === 422
}

/**
 * Formats error message for display with optional i18n support
 */
export function formatErrorForDisplay(
  error: unknown,
  options: {
    fallback?: string
    includeStatusCode?: boolean
    maxLength?: number
  } = {}
): string {
  const { fallback = 'An error occurred', includeStatusCode = false, maxLength } = options
  const info = getErrorInfo(error)
  let message = info.message

  if (includeStatusCode && info.statusCode) {
    message = `[${info.statusCode}] ${message}`
  }

  if (maxLength && message.length > maxLength) {
    message = message.slice(0, maxLength - 3) + '...'
  }

  return message || fallback
}

