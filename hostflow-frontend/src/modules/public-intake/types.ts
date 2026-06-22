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

/**
 * Step keys used by the guided public-apply flow. Mirrors the literal tuple
 * `STEP_KEYS` declared at the top of `pages/public/PublicApplyPage.tsx` so
 * page-level usage and module-level helpers stay in sync.
 */
export type StepKey =
  | 'overview'
  | 'contacts'
  | 'personal'
  | 'experience'
  | 'employment'
  | 'documents'
  | 'agreements';

/** Generic option shape for chip-style multi-select fields (trailers, routes). */
export interface MultiSelectOption {
  value: string;
  /** i18n key resolved at render time. */
  labelKey: string;
}

export type FormPresentationField = {
  qualified_code: string;
  sort_order: number;
  intake_level: string;
  label: string;
  field_type?: string | null;
  widget_hint?: string | null;
  presentation_rules?: import('../../utils/presentationRules').PresentationRules;
  evaluated?: import('../../utils/presentationRules').PresentationFieldEvaluated;
};

export type FormPresentationRuntime = {
  contract_version: string;
  entity_profile_code: string;
  presentation_code: string;
  profile_name?: string | null;
  fields: FormPresentationField[];
  warnings?: string[];
};

