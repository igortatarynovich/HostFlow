import { useState, type ReactNode } from 'react'
import { useI18n } from '../../../i18n'
import { Button } from '../../ui/Button'
import { WorkspaceSection } from '../../ui/WorkspaceSection'
import { WorkspaceTabs } from '../../ui/WorkspaceTabs'

export type CandidateCardTabId = 'personal' | 'profile' | 'documents' | 'legalization' | 'services'

const TAB_IDS: CandidateCardTabId[] = ['personal', 'profile', 'documents', 'legalization', 'services']

export function CandidateCardTabs({
  value,
  onChange,
  badges,
}: {
  value: CandidateCardTabId
  onChange: (id: CandidateCardTabId) => void
  badges?: Partial<Record<CandidateCardTabId, ReactNode>>
}) {
  const { t } = useI18n()
  return (
    <WorkspaceTabs
      ariaLabel={t('app.candidate_card.ia.tabs.personal')}
      value={value}
      onChange={(id) => onChange(id as CandidateCardTabId)}
      items={TAB_IDS.map((id) => ({
        id,
        label: t(`app.candidate_card.ia.tabs.${id}`),
        badge: badges?.[id],
      }))}
    />
  )
}

export function CardAccordion({
  title,
  description,
  summary,
  icon,
  defaultOpen = false,
  editing = false,
  onEdit,
  onDone,
  children,
}: {
  title: string
  description?: string | null
  summary?: string | null
  icon?: ReactNode
  defaultOpen?: boolean
  editing?: boolean
  onEdit?: () => void
  onDone?: () => void
  children: ReactNode
}) {
  const { t } = useI18n()
  const [open, setOpen] = useState(defaultOpen)
  const expanded = editing || open

  return (
    <WorkspaceSection
      title={title}
      description={expanded ? description || null : summary || description}
      icon={icon}
      collapsible
      open={expanded}
      onOpenChange={(next) => {
        if (!editing) setOpen(next)
      }}
      action={
        onEdit ? (
          <Button
            type="button"
            variant="link"
            className="shrink-0 text-xs"
            onClick={editing ? onDone : onEdit}
          >
            {editing ? t('app.candidate_card.ia.done') : t('common.actions.edit')}
          </Button>
        ) : null
      }
    >
      {children}
    </WorkspaceSection>
  )
}

export function joinParts(parts: Array<string | null | undefined | false>): string {
  return parts.map((part) => (typeof part === 'string' ? part.trim() : '')).filter(Boolean).join(' · ')
}
