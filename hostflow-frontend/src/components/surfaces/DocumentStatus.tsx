import { StatusBadge } from '../ui/StatusBadge'
import { documentSeverityToSemantic } from '../ui/statusBadgeSemantics'

type Props = {
  label: string
  displayStatus?: string
  severity?: 'ok' | 'warn' | 'bad' | 'info' | string
}

export default function DocumentStatus({ label, severity }: Props) {
  return (
    <StatusBadge
      label={label}
      semantic={documentSeverityToSemantic(severity)}
      size="md"
      shape="pill"
    />
  )
}
