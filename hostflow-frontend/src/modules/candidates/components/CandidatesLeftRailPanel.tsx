import type { ComponentProps } from 'react'
import { CandidatesFiltersActionsPanel } from './CandidatesFiltersActionsPanel'
import { CandidatesSavedViewsPanel } from './CandidatesSavedViewsPanel'

export type CandidatesLeftRailPanelProps = ComponentProps<typeof CandidatesFiltersActionsPanel> &
  ComponentProps<typeof CandidatesSavedViewsPanel>

export function CandidatesLeftRailPanel(props: CandidatesLeftRailPanelProps) {
  const { savedViews, onApplyView, onDeleteView, ...filtersProps } = props

  return (
    <>
      <CandidatesFiltersActionsPanel {...(filtersProps as ComponentProps<typeof CandidatesFiltersActionsPanel>)} />
      <CandidatesSavedViewsPanel
        t={props.t}
        savedViews={savedViews}
        onApplyView={onApplyView}
        onDeleteView={onDeleteView}
      />
    </>
  )
}

