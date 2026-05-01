/**
 * G-8 stage 2.2: per-document primary "next action".
 *
 * Mirrors `backend/app/modules/documents/next_action_api.py`. The backend
 * always returns a DTO (`kind: idle` when there's nothing to do); callers
 * should treat a non-200 as a hard failure rather than as "no action".
 *
 * Note: documents do not have their own SPA detail route — they live
 * inside the candidate detail page. The DTO's `href` (when set) points
 * at `/app/candidates/{candidate_id}` so badge clicks still go somewhere
 * useful.
 */
import { docsApi } from "../client";
import type { NextActionDTO } from "../nextAction";

export type DocumentNextActionDTO = NextActionDTO & { entity_type: "document" };

export async function getDocumentNextAction(documentId: string): Promise<DocumentNextActionDTO> {
  if (!documentId) {
    throw new Error("documentId is required");
  }
  const { data } = await docsApi.get<DocumentNextActionDTO>(`/documents/${documentId}/next-action`);
  return data;
}
