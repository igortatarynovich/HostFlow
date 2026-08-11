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
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
    { type: "text", key: "country", labelKey: "app.documents.fields.country", label: "Country" },
    {
      type: "multiselect",
      key: "categories",
      labelKey: "app.documents.fields.categories",
      label: "Categories",
      options: DRIVER_LICENSE_CATEGORIES.map((c) => ({ value: c, label: c })),
    },
  ],
  // Work permit
  work_permit: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "ordered_at", labelKey: "app.documents.fields.ordered_at", label: "Order date" },
    { type: "date", key: "issue_date", labelKey: "app.documents.fields.issue_date", label: "Issue date" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
    {
      type: "select",
      key: "work_permit_type",
      labelKey: "app.documents.fields.work_permit_type",
      label: "Work permit type",
      options: WORK_PERMIT_TYPES.map((t) => ({ value: t.value, label: t.fallback, labelKey: t.labelKey })),
    },
  ],
  // ADR
  adr: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expires", label: "Expires" },
    {
      type: "multiselect",
      key: "classes",
      labelKey: "app.documents.fields.adr_classes",
      label: "Classes",
      options: ADR_CLASSES.map((c) => ({ value: c, label: c })),
    },
  ],
  // ADR Certificate
  adr_certificate: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expires", label: "Expires" },
    {
      type: "multiselect",
      key: "classes",
      labelKey: "app.documents.fields.adr_classes",
      label: "Classes",
      options: ADR_CLASSES.map((c) => ({ value: c, label: c })),
    },
  ],
  // Code 95
  code95: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "issue_date", labelKey: "app.documents.fields.issue_date", label: "Issue date" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expires", label: "Expires" },
    { type: "text", key: "country", labelKey: "app.documents.fields.country", label: "Country" },
  ],
  // Qualification Code 95
  qualification_code95: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "issue_date", labelKey: "app.documents.fields.issue_date", label: "Issue date" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expires", label: "Expires" },
    { type: "text", key: "country", labelKey: "app.documents.fields.country", label: "Country" },
  ],
  // Voivodeship decision
  decision: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "issue_date", labelKey: "app.documents.fields.issue_date", label: "Issue date" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expires", label: "Expires" },
    {
      type: "select",
      key: "voivodeship",
      labelKey: "app.documents.fields.voivodeship",
      label: "Voivodeship",
      options: VOIVODESHIPS.map((v) => ({ value: v, label: v })),
    },
  ],
  // Driver certificate
  driver_certificate: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "ordered_at", labelKey: "app.documents.fields.ordered_at", label: "Order date" },
    { type: "date", key: "issue_date", labelKey: "app.documents.fields.issue_date", label: "Issue date" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
  ],
  // Passport
  passport: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
    { type: "text", key: "country", labelKey: "app.documents.fields.country", label: "Country" },
  ],
  // National ID
  national_id: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
    { type: "text", key: "country", labelKey: "app.documents.fields.country", label: "Country" },
  ],
  // EU driver license with Code 95
  eu_driver_license_code95: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
    { type: "text", key: "country", labelKey: "app.documents.fields.country", label: "Country" },
  ],
  // Identity document (alias for passport/national_id)
  identity_document: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
    { type: "text", key: "country", labelKey: "app.documents.fields.country", label: "Country" },
  ],
  // Residence permit
  residence_permit: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
    {
      type: "select",
      key: "voivodeship",
      labelKey: "app.documents.fields.voivodeship",
      label: "Voivodeship",
      options: VOIVODESHIPS.map((v) => ({ value: v, label: v })),
    },
    {
      type: "select",
      key: "residence_permit_type",
      labelKey: "app.documents.fields.residence_permit_type",
      label: "Type",
      options: RESIDENCE_PERMIT_TYPES.map((t) => ({ value: t.value, label: t.fallback, labelKey: t.labelKey })),
    },
  ],
  // Visa
  visa: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "issue_date", labelKey: "app.documents.fields.issue_date", label: "Issue date" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
    {
      type: "select",
      key: "visa_type",
      labelKey: "app.documents.fields.visa_type",
      label: "Visa type",
      options: VISA_TYPES.map((t) => ({ value: t, label: t })),
    },
  ],
  // Default for other document types
  default: [
    { type: "text", key: "number", labelKey: "app.documents.fields.number", label: "Document number" },
    { type: "date", key: "valid_from", labelKey: "app.documents.fields.valid_from", label: "Valid from" },
    { type: "date", key: "expire_date", labelKey: "app.documents.fields.expire_date", label: "Expiry date" },
  ],
};

/**
 * Get field configuration for a document type
 */
export function getDocumentFieldsConfig(docType: string): DocumentFieldConfig[] {
  return DOCUMENT_FIELDS_CONFIG[docType] || DOCUMENT_FIELDS_CONFIG.default || [];
}
