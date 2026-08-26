import React from 'react'
import { OrderProgress } from '../workspace/OrderProgress'
import { VacancyProgress } from '../workspace/VacancyProgress'
import { MainInfo } from '../workspace/MainInfo'
import { RequirementCards, type RequirementCardModel } from '../workspace/RequirementCards'
import { FunnelPanel } from '../workspace/FunnelPanel'
import { ActivityReserved } from '../workspace/ActivityReserved'
import { AttentionPanel } from '../workspace/AttentionPanel'
import { QuickActions, type QuickAction } from '../workspace/QuickActions'
import { OwnerCard } from '../workspace/OwnerCard'
import { RelatedHub, type RelatedLink } from '../workspace/RelatedHub'
import type { PipelineMetrics } from '../pipelineMetrics'

type Props = {
  metrics: PipelineMetrics
  orderLine?: { quantity_needed: number; title?: string } | null
  mainInfoRows: { label: string; value: React.ReactNode }[]
  mandatoryCards: RequirementCardModel[]
  preferredCards: RequirementCardModel[]
  preferredEmptyNote: string
  onEditRequirements: () => void
  onStageClick: (code: string) => void
  hasManager: boolean
  poolSelectedCount: number
  ownerName: string
  ownerSubtitle?: string
  quickActions: QuickAction[]
  relatedLinks: RelatedLink[]
  labels: {
    orderProgress: string
    orderHint: string
    vacancyProgress: string
    headcount: string
    hired: string
    remaining: string
    completion: string
    mainInfo: string
    requirements: string
    mandatory: string
    preferred: string
    edit: string
    funnel: string
    funnelEmpty: string
    activity: string
    activityMessage: string
    attention: string
    noRecruiter: string
    waitingDocs: string
    permit: string
    attentionEmpty: string
    quickActions: string
    owner: string
    related: string
  }
}

export function WorkspaceTab(props: Props) {
  const { labels, metrics, orderLine } = props

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        {orderLine && orderLine.quantity_needed > 0 ? (
          <OrderProgress
            title={labels.orderProgress}
            hint={labels.orderHint}
            fulfilled={metrics.hired}
            needed={orderLine.quantity_needed}
          />
        ) : null}
        <VacancyProgress
          title={labels.vacancyProgress}
          metrics={metrics}
          labels={{
            headcount: labels.headcount,
            hired: labels.hired,
            remaining: labels.remaining,
            completion: labels.completion,
          }}
        />
        <MainInfo title={labels.mainInfo} rows={props.mainInfoRows} />
        <RequirementCards
          title={labels.requirements}
          mandatoryTitle={labels.mandatory}
          preferredTitle={labels.preferred}
          preferredEmptyNote={props.preferredEmptyNote}
          mandatory={props.mandatoryCards}
          preferred={props.preferredCards}
          onEdit={props.onEditRequirements}
          editLabel={labels.edit}
        />
        <FunnelPanel
          title={labels.funnel}
          stages={metrics.stages}
          total={metrics.total}
          onStageClick={props.onStageClick}
          emptyLabel={labels.funnelEmpty}
        />
        <ActivityReserved title={labels.activity} message={labels.activityMessage} />
      </div>
      <div className="space-y-4">
        <AttentionPanel
          title={labels.attention}
          stages={metrics.stages}
          hasManager={props.hasManager}
          poolSelectedCount={props.poolSelectedCount}
          labels={{
            noRecruiter: labels.noRecruiter,
            waitingDocs: labels.waitingDocs,
            permit: labels.permit,
            empty: labels.attentionEmpty,
          }}
          onStageClick={props.onStageClick}
        />
        <QuickActions title={labels.quickActions} actions={props.quickActions} />
        <OwnerCard title={labels.owner} name={props.ownerName} subtitle={props.ownerSubtitle} />
        <RelatedHub title={labels.related} links={props.relatedLinks} />
      </div>
    </div>
  )
}
