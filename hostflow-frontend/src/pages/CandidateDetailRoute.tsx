import { useParams } from 'react-router-dom'
import { isCandidateEntityWorkspaceEnabled } from '../utils/featureFlags'
import CandidateCard from './CandidateCard'
import { CandidateEntityWorkspacePage } from './CandidateEntityWorkspacePage'

/** Routes /app/candidates/:id to Entity Workspace or legacy card (feature flag). */
export default function CandidateDetailRoute() {
  const { id } = useParams<{ id: string }>()

  if (id !== 'new' && isCandidateEntityWorkspaceEnabled()) {
    return <CandidateEntityWorkspacePage />
  }

  return <CandidateCard />
}
