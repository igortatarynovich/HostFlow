/**
 * Configuration for document field rendering based on document type
 */

export type DocumentFieldConfig = {
  type: "text" | "date" | "select" | "multiselect";
  key: string;
  /**
   * i18n key for the label (preferred). If not set, `label` is used as-is.
   */
  labelKey?: string;
  /**
   * Fallback label (also used as defaultValue for i18n).
   */
  label: string;
  options?: Array<{ value: string; label: string; labelKey?: string }>;
};

export type DocumentFieldsConfig = {
  [docType: string]: DocumentFieldConfig[];
};

export const VOIVODESHIPS = [
  "Dolnośląskie",
  "Kujawsko-pomorskie",
  "Lubelskie",
  "Lubuskie",
  "Łódzkie",
  "Małopolskie",
  "Mazowieckie",
  "Opolskie",
  "Podkarpackie",
  "Podlaskie",
  "Pomorskie",
  "Śląskie",
  "Świętokrzyskie",
  "Warmińsko-mazurskie",
  "Wielkopolskie",
  "Zachodniopomorskie",
];

export const WORK_PERMIT_TYPES = [
  { value: "type_a", labelKey: "admin.documents.forms.options.work_permit_type.type_a", fallback: "Type A" },
  { value: "declaration", labelKey: "admin.documents.forms.options.work_permit_type.declaration", fallback: "Declaration" },
];
export const RESIDENCE_PERMIT_TYPES = [
  { value: "permanent", labelKey: "admin.documents.forms.options.residence_permit_type.permanent", fallback: "Permanent" },
  { value: "temporary", labelKey: "admin.documents.forms.options.residence_permit_type.temporary", fallback: "Temporary" },
];
export const VISA_TYPES = ["C", "D"];

export const ADR_CLASSES = [
  "1",
  "2",
  "3",
  "4.1",
  "4.2",
  "4.3",
  "5.1",
  "5.2",
  "6.1",
  "6.2",
  "7",
  "8",
  "9",
];

export const DRIVER_LICENSE_CATEGORIES = [
  "A",
  "A1",
  "A2",
  "AM",
  "B",
  "B1",
  "BE",
  "C",
  "C1",
  "C1E",
  "CE",
  "D",
  "D1",
  "D1E",
  "DE",
  "T",
];

export const DOCUMENT_FIELDS_CONFIG: DocumentFieldsConfig = {
  // Driver license
  driver_license: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
    { type: "text", key: "country", labelKey: "admin.documents.forms.fields.country", label: "Страна" },
    {
      type: "multiselect",
      key: "categories",
      label: "Категории",
      options: DRIVER_LICENSE_CATEGORIES.map((c) => ({ value: c, label: c })),
    },
  ],
  // Work permit
  work_permit: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "ordered_at", labelKey: "admin.documents.forms.fields.ordered_at", label: "Дата заказа" },
    { type: "date", key: "issue_date", labelKey: "admin.documents.forms.fields.issue_date", label: "Выдан" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
    {
      type: "select",
      key: "work_permit_type",
      labelKey: "admin.documents.forms.fields.work_permit_type",
      label: "Тип разрешения на работу",
      options: WORK_PERMIT_TYPES.map((t) => ({ value: t.value, label: t.fallback, labelKey: t.labelKey })),
    },
  ],
  // ADR
  adr: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Истекает" },
    {
      type: "multiselect",
      key: "classes",
      labelKey: "admin.documents.forms.fields.adr_classes",
      label: "Классы",
      options: ADR_CLASSES.map((c) => ({ value: c, label: c })),
    },
  ],
  // ADR Certificate
  adr_certificate: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Истекает" },
    {
      type: "multiselect",
      key: "classes",
      labelKey: "admin.documents.forms.fields.adr_classes",
      label: "Классы",
      options: ADR_CLASSES.map((c) => ({ value: c, label: c })),
    },
  ],
  // Code 95
  code95: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "issue_date", labelKey: "admin.documents.forms.fields.issue_date", label: "Выдан" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Истекает" },
    { type: "text", key: "country", labelKey: "admin.documents.forms.fields.country", label: "Страна" },
  ],
  // Qualification Code 95
  qualification_code95: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "issue_date", labelKey: "admin.documents.forms.fields.issue_date", label: "Выдан" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Истекает" },
    { type: "text", key: "country", labelKey: "admin.documents.forms.fields.country", label: "Страна" },
  ],
  // Voivodeship decision
  decision: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "issue_date", labelKey: "admin.documents.forms.fields.issue_date", label: "Выдан" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Истекает" },
    {
      type: "select",
      key: "voivodeship",
      labelKey: "admin.documents.forms.fields.voivodeship",
      label: "Воеводство",
      options: VOIVODESHIPS.map((v) => ({ value: v, label: v })),
    },
  ],
  // Driver certificate
  driver_certificate: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "ordered_at", labelKey: "admin.documents.forms.fields.ordered_at", label: "Дата заказа" },
    { type: "date", key: "issue_date", labelKey: "admin.documents.forms.fields.issue_date", label: "Выдан" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
  ],
  // Passport
  passport: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
    { type: "text", key: "country", labelKey: "admin.documents.forms.fields.country", label: "Страна" },
  ],
  // National ID
  national_id: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
    { type: "text", key: "country", labelKey: "admin.documents.forms.fields.country", label: "Страна" },
  ],
  // EU driver license with Code 95
  eu_driver_license_code95: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
    { type: "text", key: "country", labelKey: "admin.documents.forms.fields.country", label: "Страна" },
  ],
  // Identity document (alias for passport/national_id)
  identity_document: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
    { type: "text", key: "country", labelKey: "admin.documents.forms.fields.country", label: "Страна" },
  ],
  // Residence permit
  residence_permit: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
    {
      type: "select",
      key: "voivodeship",
      labelKey: "admin.documents.forms.fields.voivodeship",
      label: "Воеводство",
      options: VOIVODESHIPS.map((v) => ({ value: v, label: v })),
    },
    {
      type: "select",
      key: "residence_permit_type",
      labelKey: "admin.documents.forms.fields.residence_permit_type",
      label: "Тип",
      options: RESIDENCE_PERMIT_TYPES.map((t) => ({ value: t.value, label: t.fallback, labelKey: t.labelKey })),
    },
  ],
  // Visa
  visa: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "issue_date", labelKey: "admin.documents.forms.fields.issue_date", label: "Выдан" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
    {
      type: "select",
      key: "visa_type",
      labelKey: "admin.documents.forms.fields.visa_type",
      label: "Тип визы",
      options: VISA_TYPES.map((t) => ({ value: t, label: t })),
    },
  ],
  // Default для остальных документов
  default: [
    { type: "text", key: "number", labelKey: "admin.documents.forms.fields.number", label: "Номер документа" },
    { type: "date", key: "valid_from", labelKey: "admin.documents.forms.fields.valid_from", label: "Действителен от" },
    { type: "date", key: "expire_date", labelKey: "admin.documents.forms.fields.expire_date", label: "Действителен до" },
  ],
};

/**
 * Get field configuration for a document type
 */
export function getDocumentFieldsConfig(docType: string): DocumentFieldConfig[] {
  return DOCUMENT_FIELDS_CONFIG[docType] || DOCUMENT_FIELDS_CONFIG.default || [];
}
