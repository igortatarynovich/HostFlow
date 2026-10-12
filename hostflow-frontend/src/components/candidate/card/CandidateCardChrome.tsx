import { useI18n } from '../../../i18n'
import { EntityRecordTabs } from '../../../platform/entity-workspace/entityRecordSurface'

export {
  EntityRecordSection as CardAccordion,
  EntityRecordRows as ReadRows,
  joinRecordParts as joinParts,
} from '../../../platform/entity-workspace/entityRecordSurface'

export type CandidateCardTabId = 'personal' | 'profile' | 'documents' | 'legalization' | 'services'

const TAB_IDS: CandidateCardTabId[] = ['personal', 'profile', 'documents', 'legalization', 'services']

/** Candidate card tab configuration. The tab control itself is EntityRecordTabs. */
export function CandidateCardTabs<T extends string = CandidateCardTabId>({
  value,
  onChange,
  tabs,
}: {
  value: T
  onChange: (id: T) => void
  tabs?: Array<{ id: T; label: string }>
}) {
  const { t } = useI18n()
  const items = tabs ?? TAB_IDS.map((id) => ({ id: id as T, label: t(`app.candidate_card.ia.tabs.${id}`) }))
  return <EntityRecordTabs value={value} onChange={onChange} tabs={items} />
}
