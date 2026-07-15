import type { FormPresentationField } from '../../modules/public-intake/types'
import type { FieldOption } from '../../utils/serviceSalesFieldOptions'
import { useIntakeFieldOptions } from '../../hooks/useIntakeFieldOptions'
import { PresentationFieldControl } from './PresentationFieldControl'

type FieldValue = string | string[]

type Props = {
  field: FormPresentationField
  values: Record<string, FieldValue>
  value: FieldValue
  error?: string
  disabled?: boolean
  onChange: (next: FieldValue) => void
}

export function IntakePresentationFieldControl({ field, values, value, error, disabled, onChange }: Props) {
  const options = useIntakeFieldOptions(field, values) as FieldOption[]
  const waitingForParent =
    Boolean(field.reference_meta?.depends_on_field) &&
    options.length === 0 &&
    !(field.options && field.options.length > 0)

  if (waitingForParent) {
    return <p className="text-sm text-slate-500">Сначала выберите страну</p>
  }

  return (
    <PresentationFieldControl
      field={{ ...field, options }}
      value={value}
      error={error}
      disabled={disabled || (waitingForParent && !field.reference_meta?.depends_on_field)}
      onChange={onChange}
    />
  )
}
