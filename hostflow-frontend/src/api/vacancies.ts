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
  extra?: Record<string, unknown> | string | null;
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

export async function listVacancies(params?: Record<string, unknown>) {
  const { data } = await api.get("/vacancies/", { params });
  return data;
}
