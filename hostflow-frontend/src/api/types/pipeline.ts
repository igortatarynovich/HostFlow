/**
 * Pipeline-related types
 */

import type { UUID } from './common';

/** Канбан/пайплайн */
export interface PipelineItem {
  link_id: UUID;
  candidate: { id: UUID; name?: string | null; email?: string | null };
  status: string; // код этапа
}

export interface PipelineOut {
  statuses: string[];
  columns: Record<string, PipelineItem[]>;
}

