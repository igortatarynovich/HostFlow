import React, { useMemo } from 'react'
import { SectionCard } from '../../ui/SectionCard'
import { isDocsWaitStage, isPermitStage, type StageCount } from '../pipelineMetrics'

export type AttentionItem = {
  id: string
  priority: number
  level: 'high' | 'medium' | 'low'
  text: string
  stageCode?: string
}

type Props = {
  title: string
  stages: StageCount[]
  hasManager: boolean
  poolSelectedCount: number
  labels: {
    noRecruiter: string
    waitingDocs: string
    permit: string
    empty: string
  }
  onStageClick?: (code: string) => void
}

export function AttentionPanel({
  title,
  stages,
  hasManager,
  poolSelectedCount,
  labels,
  onStageClick,
}: Props) {
  const items = useMemo(() => {
    const out: AttentionItem[] = []
    if (!hasManager && poolSelectedCount === 0) {
      out.push({
        id: 'no-recruiter',
        priority: 100,
        level: 'high',
        text: labels.noRecruiter,
      })
    }
    for (const s of stages) {
      if (s.count <= 0) continue
      if (isDocsWaitStage(s.code)) {
        out.push({
          id: `docs-${s.code}`,
          priority: 80,
          level: 'medium',
          text: labels.waitingDocs.replace('{count}', String(s.count)).replace('{stage}', s.code),
          stageCode: s.code,
        })
      } else if (isPermitStage(s.code)) {
        out.push({
          id: `permit-${s.code}`,
          priority: 60,
          level: 'medium',
          text: labels.permit.replace('{count}', String(s.count)).replace('{stage}', s.code),
          stageCode: s.code,
        })
      }
    }
    return out.sort((a, b) => b.priority - a.priority)
  }, [stages, hasManager, poolSelectedCount, labels])

  const dot = (level: AttentionItem['level']) =>
    level === 'high' ? 'bg-rose-500' : level === 'medium' ? 'bg-amber-400' : 'bg-slate-400'

  return (
    <SectionCard title={title}>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">{labels.empty}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                disabled={!item.stageCode || !onStageClick}
                onClick={() => item.stageCode && onStageClick?.(item.stageCode)}
                className="flex w-full items-start gap-2 rounded-lg px-1 py-1.5 text-left text-sm text-slate-800 enabled:hover:bg-slate-50 disabled:cursor-default"
              >
                <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${dot(item.level)}`} />
                <span>{item.text}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  )
}
