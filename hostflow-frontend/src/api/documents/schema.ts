import { docsApi } from "../client";
import { isAxios404 } from "./helpers";

// Устойчивый фетч: сначала /meta-schema, если 404 — пробуем /schema
export async function getMetaSchema(type_code: string): Promise<any> {
  if (!type_code) throw new Error("type_code is empty");
  try {
    const { data } = await docsApi.get<any>(`/document-types/${type_code}/meta-schema`);
    return data;
  } catch (e) {
    if (isAxios404(e)) {
      const { data } = await docsApi.get<any>(`/document-types/${type_code}/schema`);
      return data;
    }
    throw e;
  }
}

// Серверная валидация: основной путь /validate-meta,
// если 404 — мягкий фолбэк (считаем валидным, бэкенд всё равно проверит на PATCH)
export async function validateMeta(
  type_code: string,
  meta: Record<string, any>
): Promise<{ valid: boolean; errors?: any[] }> {
  if (!type_code) return { valid: true, errors: [] };
  try {
    const { data } = await docsApi.post<{ valid: boolean; errors?: any[] }>(
      `/document-types/${type_code}/validate-meta`,
      meta
    );
    return data;
  } catch (e) {
    if (isAxios404(e)) {
      return { valid: true, errors: [] };
    }
    throw e;
  }
}

