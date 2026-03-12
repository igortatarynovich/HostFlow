import { api } from "./client";

export type CustomFieldScope = "CANDIDATE" | "DOCUMENT";
export type CustomFieldType = "TEXT" | "TEXTAREA" | "NUMBER" | "DATE" | "CHECKBOX" | "SELECT" | "MULTISELECT";
export type CustomFieldEntityType = "CANDIDATE" | "CANDIDATE_DOCUMENT";

export interface CustomFieldDefinition {
  id: string;
  tenant_id: string;
  scope: CustomFieldScope;
  document_type_id: string | null;
  key: string;
  label: string;
  field_type: CustomFieldType;
  required: boolean;
  options: string[] | null;
  help_text: string | null;
  is_active: boolean;
  is_system: boolean;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface CustomFieldDefinitionCreate {
  scope: CustomFieldScope;
  document_type_id?: string | null;
  key: string;
  label: string;
  field_type: CustomFieldType;
  required?: boolean;
  options?: string[] | null;
  help_text?: string | null;
  is_active?: boolean;
  order?: number;
}

export interface CustomFieldDefinitionUpdate extends CustomFieldDefinitionCreate {}

export interface CustomFieldValue {
  id: string;
  tenant_id: string;
  definition_id: string;
  entity_type: CustomFieldEntityType;
  entity_id: string;
  value: any;
  updated_at: string;
  updated_by_user_id: string | null;
}

export interface CustomFieldValueSet {
  value: any;
}

export interface ListCustomFieldDefinitionsOptions {
  scope?: CustomFieldScope;
  document_type_id?: string;
  is_active?: boolean;
}

export async function listCustomFieldDefinitions(
  options?: ListCustomFieldDefinitionsOptions
): Promise<CustomFieldDefinition[]> {
  const params: Record<string, string | boolean> = {};
  if (options?.scope) {
    // Конвертируем scope в нижний регистр для бэкенда
    params.scope = options.scope.toLowerCase() as string;
  }
  if (options?.document_type_id) params.document_type_id = options.document_type_id;
  if (options?.is_active !== undefined) params.is_active = options.is_active;

  const { data } = await api.get<CustomFieldDefinition[]>("/custom-fields/definitions", { params });
  // Конвертируем scope обратно в верхний регистр для фронтенда
  return data.map((def) => ({
    ...def,
    scope: def.scope.toUpperCase() as CustomFieldScope,
  }));
}

export async function getCustomFieldDefinition(definitionId: string): Promise<CustomFieldDefinition> {
  const { data } = await api.get<CustomFieldDefinition>(`/custom-fields/definitions/${definitionId}`);
  // Конвертируем scope обратно в верхний регистр для фронтенда
  return {
    ...data,
    scope: data.scope.toUpperCase() as CustomFieldScope,
  };
}

export async function createCustomFieldDefinition(
  payload: CustomFieldDefinitionCreate
): Promise<CustomFieldDefinition> {
  // Конвертируем scope в нижний регистр для бэкенда
  const normalizedPayload = {
    ...payload,
    scope: payload.scope.toLowerCase() as string,
  };
  const { data } = await api.post<CustomFieldDefinition>("/custom-fields/definitions", normalizedPayload);
  // Конвертируем scope обратно в верхний регистр для фронтенда
  return {
    ...data,
    scope: data.scope.toUpperCase() as CustomFieldScope,
  };
}

export async function updateCustomFieldDefinition(
  definitionId: string,
  payload: CustomFieldDefinitionUpdate
): Promise<CustomFieldDefinition> {
  // Конвертируем scope в нижний регистр для бэкенда, если он присутствует
  const normalizedPayload = payload.scope
    ? {
        ...payload,
        scope: payload.scope.toLowerCase() as string,
      }
    : payload;
  const { data } = await api.patch<CustomFieldDefinition>(`/custom-fields/definitions/${definitionId}`, normalizedPayload);
  // Конвертируем scope обратно в верхний регистр для фронтенда
  return {
    ...data,
    scope: data.scope.toUpperCase() as CustomFieldScope,
  };
}

export async function deleteCustomFieldDefinition(definitionId: string): Promise<void> {
  await api.delete(`/custom-fields/definitions/${definitionId}`);
}

export interface ListCustomFieldValuesOptions {
  definition_id?: string;
  entity_type?: CustomFieldEntityType;
  entity_id?: string;
}

export async function listCustomFieldValues(
  options?: ListCustomFieldValuesOptions
): Promise<CustomFieldValue[]> {
  const params: Record<string, string> = {};
  if (options?.definition_id) params.definition_id = options.definition_id;
  if (options?.entity_type) params.entity_type = options.entity_type;
  if (options?.entity_id) params.entity_id = options.entity_id;

  const { data } = await api.get<CustomFieldValue[]>("/custom-fields/values", { params });
  return data;
}

export async function setCustomFieldValue(
  definitionId: string,
  entityType: CustomFieldEntityType,
  entityId: string,
  payload: CustomFieldValueSet
): Promise<CustomFieldValue> {
  const { data } = await api.put<CustomFieldValue>(
    `/custom-fields/values/${definitionId}/${entityType}/${entityId}`,
    payload
  );
  return data;
}

export async function deleteCustomFieldValue(
  definitionId: string,
  entityType: CustomFieldEntityType,
  entityId: string
): Promise<void> {
  await api.delete(`/custom-fields/values/${definitionId}/${entityType}/${entityId}`);
}
