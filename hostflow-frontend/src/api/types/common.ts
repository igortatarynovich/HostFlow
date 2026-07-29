/**
 * Common types used across the application
 */

export type UUID = string;

/** Текущий пользователь */
export interface WhoAmI {
  /** Stable user id (string UUID); some legacy consumers also read it via `sub`. */
  id?: string;
  email: string;
  role: 'admin' | 'manager' | 'user' | string;
  tenant_id: string;
  sub?: string;
  /** Phase 5 — `impersonation` when JWT type=impersonation; else `normal`. */
  session_kind?: 'normal' | 'impersonation' | string;
  impersonated_by?: string | null;
  exp?: number | null;
  first_name?: string | null;
  last_name?: string | null;
  full_name?: string | null;
  phone?: string | null;
  position?: string | null;
  country?: string | null;
  city?: string | null;
  birth_date?: string | null;
  avatar_url?: string | null;
  preferences?: Record<string, any> | null;
  security?: Record<string, any> | null;
}

/** Структурный адрес */
export type Address = {
  country: string; // ISO-код страны или человекочитаемое имя — на фронте строка
  city: string;
  street: string;
  house: string;
  apt: string;
  zip: string;
};

/** Cправочники */
export type Manager = { id: string; name: string; email?: string | null };
export type Country = { code: string; name: string };
export type Language = { code: string; name: string };

/** Телефонные коды: код страны -> префикс */
export type DialCodes = Record<string, string>; // { "PL": "+48", ... }

