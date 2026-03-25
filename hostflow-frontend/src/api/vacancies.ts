// src/api/vacancies.ts
import { api } from "./client";

export const EMPLOYMENT_TYPES = ["full_time", "part_time", "b2b"] as const;
export type EmploymentType = (typeof EMPLOYMENT_TYPES)[number];

export interface VacancyPayload {
  company_id: string;
  title: string;
  status?: string;
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
  /** Planned positions to fill; omit, 0, or null clears */
  headcount_target?: number | null;
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
  candidate_count?: number;
  last_candidate_activity_at?: string | null;
  headcount_target?: number | null;
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
}

export async function listVacancies(params?: ListVacanciesParams): Promise<Vacancy[]> {
  const { data } = await api.get<Vacancy[]>("/vacancies/", { params });
  return data;
}
