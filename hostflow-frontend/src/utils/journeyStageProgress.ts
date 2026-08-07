/**
 * Linear journey strip progress: a stage is "completed" only if it sits
 * before the current stage in the ordered funnel. History of visits must not
 * paint rolled-back stages as done.
 */
export function isJourneyStageCompletedByPosition(idx: number, currentIdx: number): boolean {
  return currentIdx >= 0 && idx < currentIdx
}
