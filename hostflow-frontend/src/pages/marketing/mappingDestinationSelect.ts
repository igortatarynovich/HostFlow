/** Destination picker values for MA-3. Empty is Unmapped; ignore is an explicit decision. */

export const DESTINATION_UNSET = ''
export const DESTINATION_IGNORE = '__ignore__'

export type MappingBinding = 'mapped' | 'ignored' | 'unmapped'

export function destinationSelectValue(
  binding: MappingBinding,
  destinationCode: string,
): string {
  if (binding === 'ignored') return DESTINATION_IGNORE
  return destinationCode || DESTINATION_UNSET
}

export function bindingFromDestinationSelect(
  value: string,
): { binding: MappingBinding; destination_code: string } {
  if (value === DESTINATION_IGNORE) {
    return { binding: 'ignored', destination_code: '' }
  }
  if (!value) {
    return { binding: 'unmapped', destination_code: '' }
  }
  return { binding: 'mapped', destination_code: value }
}

export function actionSelectValue(binding: MappingBinding): 'unset' | 'map' | 'ignore' {
  if (binding === 'ignored') return 'ignore'
  if (binding === 'mapped') return 'map'
  return 'unset'
}

export function bindingFromActionSelect(
  value: string,
  destinationCode: string,
): MappingBinding {
  if (value === 'ignore') return 'ignored'
  if (value === 'map' && destinationCode.trim()) return 'mapped'
  return 'unmapped'
}
