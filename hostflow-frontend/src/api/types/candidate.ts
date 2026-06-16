/**
 * Candidate-related types
 */

import type { UUID, Address } from './common';

export interface CandidateEmploymentEntry {
  employer?: string | null;
  country?: string | null;
  position?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  currently_employed?: boolean | null; // работает ли сейчас
}

export interface CandidateEmploymentRecord {
  id: UUID;
  tenant_id: UUID;
  candidate_id: UUID;
  employer_name: string;
  country?: string | null;
  position?: string | null;
  start_date: string;
  end_date?: string | null;
  currently_employed?: boolean | null; // работает ли сейчас
  trailer_types?: string[] | null;
  route_types?: string[] | null;
  truck_brands?: string[] | null;
  eu_routes?: boolean | null;
  reason_for_leaving?: string | null;
  reference_contact?: string | null;
  created_at: string;
  updated_at: string;
}

export type CandidateOpsMode = 'in_work' | 'later' | 'no_reply_needed' | 'escalated';

/** Доп. поля кандидата (extra) */
export interface CandidateExtra {
  // персональные данные
  birth_date?: string | null; // 'YYYY-MM-DD'
  citizenship?: string | null; // код страны гражданства (или имя)
  // адреса
  address?: Address; // адрес проживания
  reg_address_diff?: boolean; // адрес регистрации отличается от проживания
  reg_address?: Address; // адрес регистрации (если отличается)

  // контакты / телефон
  phone_country?: string | null; // код страны (PL/UA/…)
  phone_prefix?: string | null; // префикс "+48" (опционально, для UI)
  /** Citizenship country code mirrored from the candidate model for forms that
   *  edit `extra` (CandidatePersonalSection auto-fill from phone). */
  country_code?: string | null;
  preferred_contact?: string | null; // предпочтительный канал связи (viber/whatsapp/telegram/phone)
  first_contact_at?: string | null; // ISO8601 дата/время первого контакта

  // водительское удостоверение / опыт
  license_number?: string | null;
  license_categories?: string[] | null; // ['B','C','CE']
  experience_years?: number | null; // устарело, оставляем для совместимости
  experience_eu_years?: number | null;
  experience_non_eu_years?: number | null;
  experience_ce_total?: number | null;
  previous_employers?: string[] | null; // устаревший формат, поддерживаем чтение
  employment_history?: CandidateEmploymentEntry[] | null;
  trailer_types?: string[] | null;
  route_types?: string[] | null;
  intl_experience?: boolean | null;
  eu_routes?: boolean | null;

  // пребывание в Польше
  in_poland?: boolean | null;
  poland_stay_basis?: string | null; // visa_d / visa_c / karta_pobytu / eu_citizen / other
  current_location?: string | null; // где находится сейчас (в Польше / не в Польше / другое)

  // дополнительный опыт
  frigo_experience?: boolean | null; // опыт работы с холодильниками
  has_adr?: boolean | null; // есть ли ADR

  // документы (чек-лист)
  documents?: {
    passport?: boolean;
    driver_license?: boolean;
    medical?: boolean;
    work_permit?: boolean;
    photo?: boolean;
    contract?: boolean;
    other?: string;
  };

  // операционный режим кандидата (отдельно от этапа)
  candidate_ops?: {
    mode?: CandidateOpsMode | null;
    updated_at?: string | null;
    updated_by?: string | null;
  } | null;
}

/** Кандидат */
export interface Candidate {
  id: UUID;
  first_name: string;
  last_name: string;
  email?: string | null;
  phone?: string | null; // уже может приходить с префиксом
  phone_country_code?: string | null;
  country_code?: string | null;
  languages?: string[] | null;
  stage?: string | null;
  status_reason?: string[] | null;

  // менеджер
  manager?: string | null; // id менеджера
  manager_name?: string | null; // ФИО менеджера (для отображения)
  manager_short?: string | null; // короткий код (fallback)

  // привязки
  short_id?: string | null;
  company_id?: UUID | null; // подтягивается автоматически от вакансии
  company_name?: string | null; // название компании (read-only, для UI)
  vacancy_id?: UUID | null;
  vacancy_name?: string | null;
  recruiter_id?: UUID | null;
  recruiter_name?: string | null;
  recruiter_short?: string | null;
  source?: string | null;
  origin?: Record<string, any> | null;
  created_at?: string | null;
  updated_at?: string | null;

  // дополнительные данные
  extra?: CandidateExtra | null;
  note?: string | null;
  notes?: string | null; // легаси поле

  // прогресс документов (денормализовано для быстрого доступа)
  docs_progress?: Record<string, any> | null;
  docs_readiness_state?: string | null;
  docs_last_ordered_at?: string | null;
  docs_next_valid_from?: string | null;
  docs_has_files?: boolean | null;

  // личные данные (денормализовано из extra)
  personal_data?: Record<string, any> | null;
  contacts?: Record<string, any> | null;

  /** Client "database" view: PII masked, hide personal/contacts/documents sections */
  masked?: boolean;
  /** Handoff-based: false when agency cannot edit (accepted handoff) or client cannot edit (no accepted) */
  can_edit?: boolean;
  /** Operational permissions from GET /candidates/{id} (handoff / HR ownership). */
  permissions?: {
    operational_owner?: 'recruitment' | 'hr' | string;
    readonly_reason?: string | null;
    can_close_recruitment?: boolean;
  };
  intake_personal?: Record<string, any> | null;
  intake_contacts?: Record<string, any> | null;
  intake_experience?: Record<string, any> | null;
  intake_agreements?: Record<string, any> | null;
  /** Public intake: hiring vs client (B2B) inquiry. */
  intake_application_kind?: 'candidate' | 'client' | null;
}

export interface CandidatesListOut {
  items: Candidate[];
  total: number;
  summary: { by_stage: Record<string, number>; by_manager: Record<string, number> };
}
