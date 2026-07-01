import type { LeadMessageTemplate } from '../../../api/types'

type Props = {
  label: string
  value: string | null | undefined
  templates: LeadMessageTemplate[]
  disabled?: boolean
  onChange: (templateId: string | null) => void
  noneLabel: string
}

export default function LeadTemplateSelectField({
  label,
  value,
  templates,
  disabled = false,
  onChange,
  noneLabel,
}: Props) {
  return (
    <label className={`text-sm ${disabled ? 'text-slate-500' : 'text-slate-700'}`}>
      {label}
      <select
        className="input mt-1 w-full"
        disabled={disabled}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
      >
        <option value="">{noneLabel}</option>
        {templates.filter((tpl) => tpl.is_active).map((tpl) => (
          <option key={tpl.id} value={tpl.id}>
            {tpl.name}
          </option>
        ))}
      </select>
    </label>
  )
}
