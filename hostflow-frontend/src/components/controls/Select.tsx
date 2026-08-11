/** Legacy adapter — use `Combobox` from `components/ui/Combobox` in new code. */
import { Combobox, type ComboboxProps } from '../ui/Combobox'
import { useI18n } from '../../i18n'

export type Option = { value: string; label: string }

type Props = Omit<ComboboxProps, 'placeholder' | 'searchPlaceholder' | 'noResultsLabel'> & {
  placeholder?: string
  searchPlaceholder?: string
  noResultsLabel?: string
}

export default function Select({
  placeholder,
  searchPlaceholder,
  noResultsLabel,
  ...props
}: Props) {
  const { t } = useI18n()
  return (
    <Combobox
      {...props}
      placeholder={
        placeholder ??
        t('app.controls.select_placeholder', { defaultValue: 'Select…' })
      }
      searchPlaceholder={
        searchPlaceholder ??
        t('app.controls.search_placeholder', { defaultValue: 'Search…' })
      }
      noResultsLabel={
        noResultsLabel ?? t('app.controls.no_results', { defaultValue: 'No matches' })
      }
    />
  )
}
