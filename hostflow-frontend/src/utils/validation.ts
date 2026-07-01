/**
 * Validation utilities for form fields
 */

export function validateEmail(email: string | null | undefined): string | null {
  if (!email || !email.trim()) {
    return null // Empty email is allowed (optional field)
  }
  const trimmed = email.trim()
  // Basic email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(trimmed)) {
    return 'Invalid email format'
  }
  return null
}

export function validatePhone(phone: string | null | undefined): string | null {
  if (!phone || !phone.trim()) {
    return null // Empty phone is allowed (optional field)
  }
  const trimmed = phone.trim()
  // Remove common phone formatting characters
  const digits = trimmed.replace(/[\s()-]/g, '')
  // Check if contains only digits and optional + at start
  if (!/^\+?[\d]+$/.test(digits)) {
    return 'Phone number should contain only digits'
  }
  // Check minimum length (at least 5 digits for a valid phone number)
  if (digits.replace(/^\+/, '').length < 5) {
    return 'Phone number is too short'
  }
  // Check maximum length (reasonable limit)
  if (digits.replace(/^\+/, '').length > 15) {
    return 'Phone number is too long'
  }
  return null
}
