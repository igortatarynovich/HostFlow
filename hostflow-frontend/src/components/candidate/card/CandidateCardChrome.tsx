import type { ReactNode } from 'react'
import { useI18n } from '../../../i18n'
import { EntityRecordSection, EntityRecordTabs } from '../../../platform/entity-workspace/entityRecordSurface'

export {
  EntityRecordRows as ReadRows,
  joinRecordParts as joinParts,
} from '../../../platform/entity-workspace/entityRecordSurface'

export type CandidateCardTabId = 'personal' | 'profile' | 'documents' | 'legalization' | 'services'

const TAB_IDS: CandidateCardTabId[] = ['personal', 'profile', 'documents', 'legalization', 'services']

/** Candidate card tab configuration. The tab control itself is the workspace tab. */
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
    <EntityRecordTabs
      ariaLabel={t('app.candidate_card.ia.tabs.personal')}
      value={value}
      onChange={onChange}
      tabs={TAB_IDS.map((id) => ({
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
  return (
    <EntityRecordSection
      title={title}
      description={description}
      summary={summary}
      icon={icon}
      defaultOpen={defaultOpen}
      editing={editing}
      onEdit={onEdit}
      onDone={onDone}
    >
      {children}
    </EntityRecordSection>
  )
}
