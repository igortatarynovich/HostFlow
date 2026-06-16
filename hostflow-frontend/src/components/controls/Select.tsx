/** Legacy adapter — use `Combobox` from `components/ui/Combobox` in new code. */
import { Combobox, type ComboboxProps } from '../ui/Combobox'

export type Option = { value: string; label: string }

type Props = Omit<ComboboxProps, 'placeholder' | 'searchPlaceholder' | 'noResultsLabel'> & {
  placeholder?: string
  searchPlaceholder?: string
  noResultsLabel?: string
}

export default function Select({
  placeholder = 'Выберите…',
  searchPlaceholder = 'Поиск...',
  noResultsLabel = 'нет совпадений',
  ...props
}: Props) {
  return (
    <Combobox
      {...props}
      placeholder={placeholder}
      searchPlaceholder={searchPlaceholder}
      noResultsLabel={noResultsLabel}
    />
  )
}
