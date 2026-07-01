import { formatErrorForDisplay } from "@utils/errorHandling";

export function q<T extends Record<string, any>>(params?: T) {
  return params ? { params } : undefined;
}

export function isAxios404(err: any): boolean {
  return !!(err && err.response && err.response.status === 404);
}

export function apiErrorMessage(err: any): string {
  return formatErrorForDisplay(err, { fallback: "Network error" });
}

export function isPlainObject(value: unknown): value is Record<string, any> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

