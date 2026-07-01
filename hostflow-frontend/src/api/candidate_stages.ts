import { api } from "./client";

export interface CandidateStage {
  id: number;
  tenant_id: string | null;
  code: string;
  label: string;
  order: number;
  active: boolean;
}

export interface CandidateStageCreate {
  code: string;
  label: string;
  order?: number;
  active?: boolean;
}

export type CandidateStageUpdate = CandidateStageCreate;

export interface ListCandidateStagesOptions {
  active?: boolean;
}

export async function listCandidateStages(
  options?: ListCandidateStagesOptions
): Promise<CandidateStage[]> {
  const params: Record<string, boolean> = {};
  if (options?.active !== undefined) params.active = options.active;

  const { data } = await api.get<CandidateStage[]>("/candidate-stages", { params });
  return data;
}

export async function getCandidateStage(stageId: number): Promise<CandidateStage> {
  const { data } = await api.get<CandidateStage>(`/candidate-stages/${stageId}`);
  return data;
}

export async function createCandidateStage(
  payload: CandidateStageCreate
): Promise<CandidateStage> {
  const { data } = await api.post<CandidateStage>("/candidate-stages", payload);
  return data;
}

export async function updateCandidateStage(
  stageId: number,
  payload: CandidateStageUpdate
): Promise<CandidateStage> {
  const { data } = await api.patch<CandidateStage>(`/candidate-stages/${stageId}`, payload);
  return data;
}

export async function deleteCandidateStage(stageId: number): Promise<void> {
  await api.delete(`/candidate-stages/${stageId}`);
}
