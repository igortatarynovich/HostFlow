/**
 * Type definitions for public intake module
 */

export type IntakeStep =
  | 'language'
  | 'contacts'
  | 'questions'
  | 'employment'
  | 'documents'
  | 'review'
  | 'thank_you'
  | 'overview';

export type QuestionId =
  | 'location'
  | 'citizenship'
  | 'stay_basis'
  | 'ce_experience'
  | 'trailer_types'
  | 'frigo_experience'
  | 'intl_experience'
  | 'has_adr'
  | 'birth_date';

export type DocumentStatus = 'uploaded' | 'missing' | 'in_progress';

export type DocumentType =
  | 'driver_license_code95'
  | 'driver_license'
  | 'code95'
  | 'tachograph_card'
  | 'residence_permit'
  | 'voivodeship_decision'
  | 'passport'
  | 'psych_tests'
  | 'adr';

export interface QuestionAnswer {
  questionId: QuestionId;
  value: any;
}

export interface EmploymentEntry {
  id?: string | null;
  position?: string;
  employer_name: string;
  country: string;
  start_date: string;
  end_date?: string | null;
  currently_employed: boolean;
}

export interface DocumentEntry {
  type: DocumentType;
  status: DocumentStatus;
  files?: File[];
}

