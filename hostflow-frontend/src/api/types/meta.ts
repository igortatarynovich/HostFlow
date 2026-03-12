/**
 * Metadata and other types
 */

import type { Candidate } from './candidate';

/** Метаданные этапов */
export interface MetaStages {
  default: string;
  codes: string[];
  labels: Record<string, string>; // code -> human label
  groups: Record<string, string[]>; // column -> codes[]
  column_of: Record<string, string>; // code -> column
  order: string[]; // ordered codes
  reason_choices?: Record<string, { code: string; label: string }[]>;
  custom_stages?: Array<{ code: string; label: string; order: number; id: string | number }>;
  funnel_id?: string; // when using funnel-based stages
}

/** Запрос на удаление (расширенный для UI) */
export interface DeletionRequest {
  id: string;
  user_id?: string; // может отсутствовать, если денормализовано
  reason?: string; // не всегда приходит
  requested_at: string;
  status: 'pending' | 'approved' | 'rejected';

  // Денормализованные поля, которые читает фронт
  candidate_id?: string;
  candidate?: any; // { first_name, last_name, ... }

  requested_by_user?: any; // User объект
  requested_by?: string; // fallback строка, если user не пришёл

  supervisor_user?: any;
  supervisor_id?: string;

  resolved_by?: string;
  resolved_at?: string;
}

/** Решение по запросу на удаление */
export interface DeletionDecision {
  request_id?: string;
  decided_by?: string;
  decision?: 'approved' | 'rejected';
  decided_at?: string;
  // поле, которое отправляет UI при отклонении
  comment?: string;
  // совместимость с прежним наименованием
  notes?: string | null;
}

