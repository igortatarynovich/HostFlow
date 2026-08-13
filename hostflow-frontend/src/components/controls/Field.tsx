import { FormField, type FormFieldProps } from '../ui/FormField'

/** Legacy alias — use `FormField` from the UI kit in new code. */
export default function Field(props: FormFieldProps) {
  return <FormField {...props} />
}
