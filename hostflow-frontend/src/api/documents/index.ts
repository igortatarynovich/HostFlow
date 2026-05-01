/**
 * Documents API - Modular structure
 * 
 * This module is split into smaller modules for better maintainability:
 * - types.ts - Type definitions
 * - normalize.ts - Data normalization functions
 * - helpers.ts - Utility functions
 * - catalog.ts - Document types catalog
 * - list.ts - Document listing operations
 * - crud.ts - Create, read, update, delete operations
 * - check.ts - Document approval/rejection
 * - extract.ts - OCR/extraction operations
 * - upload.ts - File upload operations
 * - summary.ts - Summary and checklist operations
 * - export.ts - Export operations
 * - file.ts - File download operations
 * - schema.ts - Schema validation
 * - ruleset.ts - Ruleset operations
 */

// Re-export all types
export type {
  DocType,
  PresignUpload,
  RulesetVersionCreateInput,
  RulesetRollbackInput,
  CreateCandidateDocumentPayload,
  DocumentPatchPayload,
  DocumentOrderInput,
  ListDocumentsOptions,
  ExtractResult,
  DocumentFileDownload,
} from "./types";

// Re-export all functions
export { getDocumentTypes } from "./catalog";
export { listDocuments, listCandidateDocuments, getDocument, listDocumentChecks } from "./list";
export {
  createCandidateDocument,
  orderDocument,
  patchDocument,
  deleteDocument,
} from "./crud";
export {
  listDocumentTemplates,
  getDocumentTemplate,
  applyDocumentTemplate,
} from "./templates";
export type { DocumentTemplate, ApplyTemplatePayload, AppliedTemplateResponse } from "./templates";
export {
  listDocumentPolicies,
  getDocumentPolicy,
  createDocumentPolicy,
  updateDocumentPolicy,
  deleteDocumentPolicy,
} from "./policies";
export type {
  DocumentPolicy,
  DocumentPolicyScope,
  DocumentPolicyCreate,
  DocumentPolicyUpdate,
  ListDocumentPoliciesOptions,
} from "./policies";
export { checkDocument, postDocumentCheck } from "./check";
export { extractDocument } from "./extract";
export { presignUpload, uploadViaPresign, mockUpload } from "./upload";
export { getSummary, getChecklist } from "./summary";
export { exportDocumentsJSON, exportDocumentsCSV, exportCandidateBundle } from "./export";
export { downloadDocumentFile, getDocumentFileUrl } from "./file";
export { getMetaSchema, validateMeta } from "./schema";
export {
  getRuleset,
  patchRuleset,
  putRuleset,
  listRulesetVersions,
  getRulesetVersionById,
  createRulesetVersion,
  activateRulesetVersion,
  rollbackRulesetVersion,
  getRulesetDiff,
  getRulesetUsage,
} from "./ruleset";
export { getDocumentNextAction } from "./nextAction";
export type { DocumentNextActionDTO } from "./nextAction";

// Re-export normalization functions (for advanced use cases)
export {
  normalizeDocument,
  normalizeCheck,
  normalizeFile,
  normalizeWorkflow,
  normalizeSummaryResponse,
  normalizeDocumentSummary,
  normalizeChecklist,
  normalizeReminder,
  normalizeStatus,
  normalizeKind,
  normalizeRequestedFrom,
  normalizeProcessType,
  normalizeReadinessState,
  normalizeDateInput,
  normalizeDateTime,
  normalizeWorkflowStep,
  normalizeWorkflowStepStatus,
} from "./normalize";

