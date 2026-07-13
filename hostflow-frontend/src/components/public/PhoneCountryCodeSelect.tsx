import Select from '../controls/Select'
import { resolveDialCodeValue, useDialCodeOptions } from '../../hooks/useDialCodeOptions'
import { useI18n } from '../../i18n'

type Props = {
  value: string
  onChange: (dialCode: string) => void
  disabled?: boolean
  className?: string
}

export default function PhoneCountryCodeSelect({ value, onChange, disabled, className }: Props) {
  const { t } = useI18n()
  const { options, loading } = useDialCodeOptions()
  const resolvedValue = resolveDialCodeValue(value, options)

  return (
    <Select
      options={options}
      value={resolvedValue}
      onChange={onChange}
      disabled={disabled || loading || options.length === 0}
      className={className}
      placeholder={t('public.intake.forms.contacts.country_code', { defaultValue: 'Country code' })}
      searchPlaceholder={t('app.candidate_card.select.search_country', { defaultValue: 'Search country' })}
      noResultsLabel={t('common.no_results', { defaultValue: 'No results' })}
    />
  )
}
