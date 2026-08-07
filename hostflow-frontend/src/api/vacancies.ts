// src/api/vacancies.ts
import { api } from "./client";
import type { NextActionDTO } from "./nextAction";
import type { SearchRole } from "../utils/launchSearchRoleDefaults";

export const EMPLOYMENT_TYPES = ["full_time", "part_time", "b2b"] as const;
export type EmploymentType = (typeof EMPLOYMENT_TYPES)[number];

/**
 * Canonical vacancy lifecycle states. Mirrors the backend `VacancyStatus`
 * enum in `backend/app/models/vacancy.py`. See the contract spec at
 * `docs/specs/vacancy-statuses.md`.
 *
 * The backend `VacancyOut` schema normalizes legacy `paused` rows to
 * `on_hold` before they reach the wire, so the UI can rely on this
 * canonical set when rendering badges and filtering lists.
 */
export const VACANCY_STATUSES = [
  "open",
  "on_hold",
  "closed",
  "filled",
  "cancelled",
] as const;
export type VacancyStatus = (typeof VACANCY_STATUSES)[number];

/**
 * Coerce any string the wire might still serve into a canonical
 * `VacancyStatus`. Hardens the UI against rows the Stage B alembic
 * backfill has not yet rewritten and against bespoke statuses an
 * earlier admin tool may have stored.
 *
 * Aliases: `paused → on_hold`. Unknown values fall back to `open` so
 * the badge renders something instead of erroring out.
 */
export function normalizeVacancyStatus(raw: unknown): VacancyStatus {
  if (typeof raw !== "string") return "open";
  const text = raw.trim().toLowerCase();
  if (!text) return "open";
  if ((VACANCY_STATUSES as readonly string[]).includes(text)) {
    return text as VacancyStatus;
  }
  if (text === "paused") return "on_hold";
  return "open";
}

export interface VacancyPayload {
  company_id: string;
  title: string;
  status?: VacancyStatus | string;
  description?: string | null;
  location?: string | null;
  employment_type: EmploymentType;
  salary_from?: number | string | null;
  salary_to?: number | string | null;
  currency?: string | null;
  is_active?: boolean;
  is_archived?: boolean;
  is_open?: boolean;
  candidate_profile_id?: string | null;
  /** Recruitment Pipeline assignment (ADR-035 §12) */
  funnel_id?: string | null;
  /** Planned positions to fill; omit, 0, or null clears */
  headcount_target?: number | null;
  /** ADR-032: Sales Order Line bind (1:1) */
  order_line_id?: string | null;
  extra?: Record<string, unknown> | string | null;
}

export interface Vacancy {
  id: string;
  company_id: string;
  title: string;
  status: string;
  description?: string | null;
  location?: string | null;
  company_name?: string | null;
  currency?: string | null;
  is_open?: boolean | null;
  is_active?: boolean | null;
  is_archived?: boolean | null;
  candidate_profile_id?: string | null;
  candidate_profile_name?: string | null;
  funnel_id?: string | null;
  candidate_count?: number;
  last_candidate_activity_at?: string | null;
  headcount_target?: number | null;
  order_line_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export async function createVacancy(payload: VacancyPayload) {
  const { data } = await api.post("/vacancies/", payload);
  return data;
}

export async function updateVacancy(id: string, payload: Partial<VacancyPayload>) {
  const { data } = await api.patch(`/vacancies/${id}`, payload);
  return data;
}

export async function getVacancy(id: string) {
  const { data } = await api.get(`/vacancies/${id}`);
  return data;
}

export interface ListVacanciesParams {
  company_id?: string;
  status?: string;
  candidate_profile_id?: string;
  q?: string;
  limit?: number;
  offset?: number;
  order_by?: string;
  desc?: string | boolean;
  /** Server-side filter: include archived vacancies (default false). */
  is_archived?: boolean;
}

export async function listVacancies(params?: ListVacanciesParams): Promise<Vacancy[]> {
  const { data } = await api.get<Vacancy[]>("/vacancies/", { params });
  return data;
}

/**
 * G-8 stage 2.1: per-vacancy primary "next action".
 *
 * Mirrors `backend/app/api/v1/vacancies/next_action_api.py`. The backend
 * always returns a DTO (`kind: idle` when there's nothing to do); callers
 * should treat a non-200 as a hard failure rather than as "no action".
 */
export type VacancyNextActionDTO = NextActionDTO & { entity_type: "vacancy" };

export async function getVacancyNextAction(vacancyId: string): Promise<VacancyNextActionDTO> {
  if (!vacancyId) {
    throw new Error("vacancyId is required");
  }
  const { data } = await api.get<VacancyNextActionDTO>(`/vacancies/${vacancyId}/next-action`);
  return data;
}

/** Bind launch-search defaults (profile + funnel) after vacancy stub creation. */
export async function setupLaunchSearchVacancy(
  vacancyId: string,
  role: SearchRole,
): Promise<{ funnel_id: string | null }> {
  const { data } = await api.post<{ funnel_id: string | null }>(
    `/vacancies/${vacancyId}/launch-search/setup`,
    { role },
  );
  const funnelId = typeof data?.funnel_id === "string" ? data.funnel_id : null;
  if (!funnelId) {
    throw new Error("Launch search setup did not return a funnel_id");
  }
  return { funnel_id: funnelId };
}
