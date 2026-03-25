import type { ComponentProps } from 'react'
import { CandidatesFiltersActionsPanel } from './CandidatesFiltersActionsPanel'

export type CandidatesLeftRailPanelProps = ComponentProps<typeof CandidatesFiltersActionsPanel>

export function CandidatesLeftRailPanel(props: CandidatesLeftRailPanelProps) {
  return <CandidatesFiltersActionsPanel {...props} />
}
