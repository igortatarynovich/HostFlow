import { docsApi } from "../client";
import type { Document } from "../types";
import type {
  CreateCandidateDocumentPayload,
  DocumentOrderInput,
  DocumentPatchPayload,
} from "./types";
import { isPlainObject, apiErrorMessage } from "./helpers";
import { normalizeDocument } from "./normalize";

export async function createCandidateDocument(
  payload: CreateCandidateDocumentPayload
): Promise<Document> {
  if (!payload?.owner_id) {
    throw new Error("owner_id is required to create a document");
  }
  const path = `/candidate/${payload.owner_id}/documents`;
  const resolvedDocType = (
    payload.doc_type ??
    payload.type_code ??
    payload.meta?.doc_type ??
    payload.meta_json?.doc_type ??
    ""
  ).toString().trim();
  if (!resolvedDocType) {
    throw new Error("doc_type (type_code) is required to create a document");
  }

  // DocumentCreateIn принимает issue_date или issued_at, expire_date или expires_at через aliases
  // Фильтруем пустые строки, чтобы не отправлять их в backend
  const issueDate = payload.issue_date ?? payload.issued_at ?? null;
  const expireDate = payload.expire_date ?? payload.expires_at ?? null;
  const cleanIssueDate = (issueDate && typeof issueDate === "string" && issueDate.trim()) ? issueDate.trim() : null;
  const cleanExpireDate = (expireDate && typeof expireDate === "string" && expireDate.trim()) ? expireDate.trim() : null;

  const metaBase = payload.meta_json ?? payload.meta ?? {};
  const metaPayload: Record<string, any> = isPlainObject(metaBase) ? { ...metaBase } : {};
  if (payload.title !== undefined) {
    metaPayload.title = payload.title;
  }
  if (payload.number !== undefined) {
    metaPayload.number = payload.number;
  }
  if (payload.custom_name !== undefined && payload.custom_name !== null) {
    metaPayload.custom_name = payload.custom_name;
  }
  
  // Для additional_document, если custom_name не задан, но есть title в meta, используем его
  if (resolvedDocType === "additional_document" && !payload.custom_name && metaPayload.title) {
    // title уже будет использован ниже в effectiveCustomName
  }

  const body: Record<string, any> = {
    doc_type: resolvedDocType,
  };

  // Добавляем опциональные поля только если они заданы
  if (payload.kind) body.kind = payload.kind;
  if (payload.requested_from) body.requested_from = payload.requested_from;
  if (payload.process_type) body.process_type = payload.process_type;
  if (payload.status) body.status = payload.status;
  if (payload.number !== undefined && payload.number !== null) body.number = payload.number;
  // DocumentCreateIn принимает issue_date или issued_at через alias
  if (cleanIssueDate !== null) body.issue_date = cleanIssueDate;
  // DocumentCreateIn принимает expire_date или expires_at через alias
  if (cleanExpireDate !== null) body.expire_date = cleanExpireDate;
  // Фильтруем пустые строки для дат
  if (payload.ordered_at && typeof payload.ordered_at === "string" && payload.ordered_at.trim()) {
    body.ordered_at = payload.ordered_at.trim();
  }
  if (payload.valid_from && typeof payload.valid_from === "string" && payload.valid_from.trim()) {
    body.valid_from = payload.valid_from.trim();
  }
  if (payload.reminder_days_before !== undefined && payload.reminder_days_before !== null) {
    body.reminder_days_before = payload.reminder_days_before;
  }
  if (payload.workflow) body.workflow = payload.workflow;

  // Для 'other' и 'additional_document' используем title как custom_name, если custom_name не задан
  // Также проверяем meta.title и meta_json.title, так как title может быть там
  const metaJson = payload.meta_json ?? payload.meta ?? {};
  const titleValue = payload.title ?? metaPayload.title ?? metaJson.title;
  let effectiveCustomName =
    payload.custom_name ??
    ((resolvedDocType === "other" || resolvedDocType === "additional_document")
      ? (titleValue ?? null)
      : undefined);
  
  // Для additional_document custom_name обязателен - если его нет, это критическая ошибка
  if (resolvedDocType === "additional_document" && !effectiveCustomName) {
    console.error("[createCandidateDocument] additional_document requires custom_name, but it's missing!", {
      payload,
      metaPayload,
      metaJson,
      titleValue,
      resolvedDocType,
      "payload.custom_name": payload.custom_name,
      "payload.title": payload.title,
      "metaPayload.title": metaPayload.title,
      "metaJson.title": metaJson.title
    });
    // Попробуем найти title в meta_json напрямую
    if (metaJson.title && typeof metaJson.title === "string") {
      effectiveCustomName = metaJson.title.trim();
      console.warn("[createCandidateDocument] Using meta_json.title as custom_name:", effectiveCustomName);
    }
  }
  
  // КРИТИЧНО: Для additional_document custom_name должен быть установлен принудительно
  if (resolvedDocType === "additional_document") {
    if (effectiveCustomName && effectiveCustomName !== "") {
      body.custom_name = String(effectiveCustomName).trim();
      console.log("[createCandidateDocument] Set custom_name for additional_document:", body.custom_name);
    } else {
      // Если custom_name все еще отсутствует, используем дефолтное значение
      body.custom_name = "Additional Document";
      console.warn("[createCandidateDocument] Using default custom_name for additional_document:", body.custom_name);
    }
  } else if (effectiveCustomName !== undefined && effectiveCustomName !== null && effectiveCustomName !== "") {
    body.custom_name = String(effectiveCustomName).trim();
    console.log("[createCandidateDocument] Set custom_name:", body.custom_name);
  }

  if (Object.keys(metaPayload).length > 0) {
    body.meta = metaPayload;
  }
  
  // Для additional_document user_comment обязателен
  if (resolvedDocType === "additional_document") {
    const userComment = payload.user_comment ?? metaPayload.user_comment ?? metaPayload.comment ?? metaJson.user_comment ?? metaJson.comment;
    if (userComment && typeof userComment === "string" && userComment.trim()) {
      body.user_comment = userComment.trim();
    } else if (!body.user_comment) {
      // Если user_comment отсутствует, используем дефолтное значение
      body.user_comment = "Created from checklist";
      console.warn("[createCandidateDocument] Using default user_comment for additional_document:", body.user_comment);
    }
  }

  try {
    console.log("[createCandidateDocument] Sending request:", { path, body, payload });
    const { data } = await docsApi.post(path, body);
    return normalizeDocument(data as any);
  } catch (e: any) {
    console.error("[createCandidateDocument] Error:", e?.response?.data || e?.message || e);
    throw new Error(apiErrorMessage(e));
  }
}

export async function orderDocument(payload: DocumentOrderInput): Promise<Document> {
  if (!payload?.candidate_id) {
    throw new Error("candidate_id is required");
  }
  if (!payload.doc_type) {
    throw new Error("doc_type is required");
  }
  const body: Record<string, any> = {
    candidate_id: payload.candidate_id,
    doc_type: payload.doc_type,
  };
  if (payload.ordered_at) body.ordered_at = payload.ordered_at;
  if (payload.requested_from) body.requested_from = payload.requested_from;
  if (payload.owner_context && Object.keys(payload.owner_context).length > 0) {
    body.owner_context = payload.owner_context;
  }
  const { data } = await docsApi.post(`/documents/order`, body);
  return normalizeDocument(data as any);
}

export async function patchDocument(docId: string, patch: DocumentPatchPayload): Promise<Document> {
  const body: Record<string, any> = {};

  if (patch.doc_type) {
    body.doc_type = patch.doc_type;
    body.type = patch.doc_type;
    body.type_code = patch.doc_type;
  }
  if (patch.kind) body.kind = patch.kind;
  if (patch.requested_from) body.requested_from = patch.requested_from;
  if (patch.process_type) body.process_type = patch.process_type;
  if (patch.custom_name !== undefined) body.custom_name = patch.custom_name;
  if (patch.number !== undefined) body.number = patch.number;
  if (patch.status) body.status = patch.status;
  if (patch.issue_date !== undefined || patch.issued_at !== undefined) {
    body.issue_date = patch.issue_date ?? patch.issued_at ?? null;
  }
  if (patch.expire_date !== undefined || patch.expires_at !== undefined) {
    body.expire_date = patch.expire_date ?? patch.expires_at ?? null;
  }
  if (patch.ordered_at !== undefined) {
    body.ordered_at = patch.ordered_at;
  }
  if (patch.valid_from !== undefined) {
    body.valid_from = patch.valid_from;
  }
  if (patch.reminder_days_before !== undefined) {
    body.reminder_days_before = patch.reminder_days_before;
  }
  if (patch.owner_id !== undefined) body.owner_id = patch.owner_id;
  if (patch.owner_type !== undefined) body.owner_type = patch.owner_type;
  if (patch.company_id !== undefined) body.company_id = patch.company_id;
  if (patch.workflow !== undefined) body.workflow = patch.workflow;
  if (patch.files !== undefined) body.files = patch.files;
  if (patch.source !== undefined) body.source = patch.source;
  if (patch.external_id !== undefined) body.external_id = patch.external_id;

  const metaBase = patch.meta_json ?? patch.meta;
  let metaPayload: Record<string, any> | null = isPlainObject(metaBase) ? { ...metaBase } : null;
  if (patch.title !== undefined) {
    if (!metaPayload) metaPayload = {};
    metaPayload.title = patch.title;
  }
  if (patch.custom_name !== undefined) {
    if (!metaPayload) metaPayload = {};
    metaPayload.custom_name = patch.custom_name;
  }
  if (patch.number !== undefined) {
    if (!metaPayload) metaPayload = {};
    metaPayload.number = patch.number;
  }
  if (metaPayload) {
    body.meta = metaPayload;
  }

  try {
    const { data } = await docsApi.patch(`/documents/${docId}`, body);
    return normalizeDocument(data as any);
  } catch (e: any) {
    throw new Error(apiErrorMessage(e));
  }
}

export async function deleteDocument(docId: string): Promise<void> {
  await docsApi.delete(`/documents/${docId}`);
}

