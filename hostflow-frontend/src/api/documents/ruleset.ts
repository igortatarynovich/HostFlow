import { docsApi } from "../client";
import type { RulesetDiff, RulesetUsageResponse, RulesetVersion } from "../types";
import type { RulesetVersionCreateInput, RulesetRollbackInput } from "./types";
import { q } from "./helpers";

export async function getRuleset(): Promise<RulesetVersion> {
  const { data } = await docsApi.get<RulesetVersion>(`/ruleset`);
  return data;
}

export async function patchRuleset(body: any): Promise<RulesetVersion> {
  const { data } = await docsApi.patch<RulesetVersion>(`/ruleset`, body);
  return data;
}

export const putRuleset = patchRuleset;

export async function listRulesetVersions(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<RulesetVersion[]> {
  const { data } = await docsApi.get<RulesetVersion[]>(`/ruleset/versions`, q(params));
  return data;
}

export async function getRulesetVersionById(id: string): Promise<RulesetVersion> {
  const { data } = await docsApi.get<RulesetVersion>(`/ruleset/versions/${id}`);
  return data;
}

export async function createRulesetVersion(
  payload: RulesetVersionCreateInput
): Promise<RulesetVersion> {
  const { data } = await docsApi.post<RulesetVersion>(`/ruleset/versions`, payload);
  return data;
}

export async function activateRulesetVersion(id: string): Promise<RulesetVersion> {
  const { data } = await docsApi.post<RulesetVersion>(`/ruleset/versions/${id}/activate`, {});
  return data;
}

export async function rollbackRulesetVersion(
  id: string,
  payload: RulesetRollbackInput
): Promise<RulesetVersion> {
  const { data } = await docsApi.post<RulesetVersion>(`/ruleset/versions/${id}/rollback`, payload);
  return data;
}

export async function getRulesetDiff(
  id: string,
  compareTo?: string | null
): Promise<RulesetDiff> {
  const { data } = await docsApi.get<RulesetDiff>(
    `/ruleset/versions/${id}/diff`,
    q(compareTo ? { compare_to: compareTo } : undefined)
  );
  return data;
}

export async function getRulesetUsage(params?: {
  used_in?: string;
  since?: string;
  until?: string;
  limit?: number;
}): Promise<RulesetUsageResponse> {
  const { data } = await docsApi.get<RulesetUsageResponse>(`/ruleset/usage`, q(params));
  return data;
}

