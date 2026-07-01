import { api } from "./client";

export interface CandidateProfile {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  description: string | null;
  client_id: string | null;
  funnel_id?: string | null;
  config: Record<string, any>;
  is_active: boolean;
  is_system: boolean;
  owner_user_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  usage_count?: number | null; // Number of vacancies using this profile
}

export interface CandidateProfileCreate {
  code: string;
  name: string;
  description?: string | null;
  client_id?: string | null;
  funnel_id?: string | null;
  config?: Record<string, any>;
  owner_user_id?: string | null;
  notes?: string | null;
}

export type CandidateProfileUpdate = CandidateProfileCreate;

export interface ListCandidateProfilesOptions {
  client_id?: string;
  is_active?: boolean;
}

export async function listCandidateProfiles(
  options?: ListCandidateProfilesOptions
): Promise<CandidateProfile[]> {
  const params: Record<string, string | boolean> = {};
  if (options?.client_id) params.client_id = options.client_id;
  if (options?.is_active !== undefined) params.is_active = options.is_active;

  const { data } = await api.get<CandidateProfile[]>("/candidate-profiles", { params });
  return data;
}

export async function getCandidateProfile(profileId: string): Promise<CandidateProfile> {
  const { data } = await api.get<CandidateProfile>(`/candidate-profiles/${profileId}`);
  return data;
}

export async function createCandidateProfile(
  payload: CandidateProfileCreate
): Promise<CandidateProfile> {
  const { data } = await api.post<CandidateProfile>("/candidate-profiles", payload);
  return data;
}

export async function updateCandidateProfile(
  profileId: string,
  payload: CandidateProfileUpdate
): Promise<CandidateProfile> {
  const { data } = await api.patch<CandidateProfile>(`/candidate-profiles/${profileId}`, payload);
  return data;
}

export async function deleteCandidateProfile(profileId: string): Promise<void> {
  await api.delete(`/candidate-profiles/${profileId}`);
}

export interface FixOrphanedVacanciesResult {
  updated: number;
  default_profile_id: string;
}

/** Set candidate_profile_id to driver_ce_default for vacancies with no profile or with missing/inactive profile. */
export async function fixOrphanedVacancies(): Promise<FixOrphanedVacanciesResult> {
  const { data } = await api.post<FixOrphanedVacanciesResult>(
    "/candidate-profiles/fix-orphaned-vacancies"
  );
  return data;
}

export interface ProfileLimits {
  plan: string;
  limits: {
    simple: { used: number; limit: number; available: number };
    medium: { used: number; limit: number; available: number };
    resource: { used: number; limit: number; available: number };
    total_custom: { used: number; limit: number; available: number };
  };
  field_categories: Record<string, string>;
}

export async function getProfileLimits(): Promise<ProfileLimits> {
  const { data } = await api.get<ProfileLimits>("/candidate-profiles/limits");
  return data;
}

export interface ProfileHistoryEntry {
  id: string;
  action: string;
  old_data: Record<string, any> | null;
  new_data: Record<string, any> | null;
  changes: Record<string, any> | null;
  comment: string | null;
  actor_id: string | null;
  actor_name: string | null;
  created_at: string | null;
}

export async function getProfileHistory(
  profileId: string,
  limit?: number
): Promise<ProfileHistoryEntry[]> {
  const params: Record<string, number> = {};
  if (limit !== undefined) params.limit = limit;

  const { data } = await api.get<ProfileHistoryEntry[]>(
    `/candidate-profiles/${profileId}/history`,
    { params }
  );
  return data;
}

export interface CandidateProfileFieldContractField {
  code: string;
  section: string;
  required: boolean;
  owner: string;
  source_of_truth: string;
  editable_by: string[];
  purpose?: string | null;
  aliases: string[];
}

export interface CandidateProfileFieldContract {
  profile_id: string;
  profile_code: string;
  profile_name: string;
  contract_version: number;
  fields: CandidateProfileFieldContractField[];
}

export async function getCandidateProfileFieldContract(
  profileId: string
): Promise<CandidateProfileFieldContract> {
  const { data } = await api.get<CandidateProfileFieldContract>(
    `/candidate-profiles/${profileId}/field-contract`
  );
  return data;
}
