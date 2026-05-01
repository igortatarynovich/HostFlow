import type { Document, DocumentWorkflow, DocumentWorkflowStep } from '../../api/types/document'

/** Step is done if backend set completed_at or normalized status is done. */
export function isWorkflowStepDone(step: DocumentWorkflowStep): boolean {
  if (step.completed_at) return true
  const s = String(step.status || '').toLowerCase()
  return s === 'done' || s === 'completed' || s === 'approved' || s === 'finished'
}

export function hasWorkflowOverdueStep(doc: Document, nowMs: number): boolean {
  if (doc.kind !== 'process') return false
  const steps = doc.workflow?.steps
  if (!Array.isArray(steps) || !steps.length) return false
  return steps.some((st) => {
    if (isWorkflowStepDone(st)) return false
    const due = st.due_at
    if (!due) return false
    const t = Date.parse(due)
    if (Number.isNaN(t)) return false
    return t < nowMs
  })
}

/**
 * Mark a single step completed (sets completed_at ISO). Preserves other step fields;
 * server normalize_workflow will recompute status/current_step.
 */
export function withStepCompleted(
  workflow: DocumentWorkflow | null | undefined,
  stepCode: string,
  actorId?: string | null,
): DocumentWorkflow | null {
  if (!workflow || !Array.isArray(workflow.steps)) return workflow ?? null
  const iso = new Date().toISOString()
  const steps = workflow.steps.map((st) => {
    if (st.code !== stepCode) return { ...st }
    const next: DocumentWorkflowStep = {
      ...st,
      status: 'done' as DocumentWorkflowStep['status'],
      completed_at: iso,
    }
    if (actorId) {
      const meta = { ...(st.meta || {}), completed_by: actorId }
      next.meta = meta
    }
    return next
  })
  return { ...workflow, steps }
}

export function isProcessDocument(doc: Document): boolean {
  return doc.kind === 'process'
}

/** True when no step is in progress but at least one step is unfinished (matches workflow “Order” / start). */
export function workflowCanStart(doc: Document): boolean {
  if (!isProcessDocument(doc)) return false
  const steps = doc.workflow?.steps
  if (!Array.isArray(steps) || !steps.length) return false
  const hasActive = steps.some((step) => String(step.status || '').toLowerCase() === 'in_progress')
  const unfinishedExists = steps.some((step) => !isWorkflowStepDone(step))
  return !hasActive && unfinishedExists
}

/** Overdue SLA on a step, or process not yet started when steps exist. */
export function documentProcessNeedsAttention(doc: Document, nowMs: number): boolean {
  return hasWorkflowOverdueStep(doc, nowMs) || workflowCanStart(doc)
}

export function isProcessAssignedToUser(doc: Document, userId: string | null | undefined): boolean {
  if (!userId || !isProcessDocument(doc)) return false
  const uid = String(userId)
  if (doc.owner_id != null && String(doc.owner_id) === uid) return true
  if (doc.responsible_user_id != null && String(doc.responsible_user_id) === uid) return true
  return false
}
