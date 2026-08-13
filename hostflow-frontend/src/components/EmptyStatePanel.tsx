import { EmptyState, type EmptyStateAction, type EmptyStateProps } from './ui/EmptyState'

type Action = EmptyStateAction & { variant?: 'primary' | 'secondary' }

type EmptyStatePanelProps = EmptyStateProps & {
  primaryAction?: Action
  secondaryAction?: Action
}

/** Legacy alias — use `EmptyState` from the UI kit in new code. */
export default function EmptyStatePanel(props: EmptyStatePanelProps) {
  return <EmptyState {...props} />
}
