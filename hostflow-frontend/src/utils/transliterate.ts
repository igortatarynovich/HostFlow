/** Cyrillic detection for normalization hints */

const CYRILLIC_PATTERN = /[\u0400-\u04FF\u0500-\u052F]/

export function hasCyrillic(text: string | null | undefined): boolean {
  if (!text || typeof text !== 'string') return false
  return CYRILLIC_PATTERN.test(text)
}
