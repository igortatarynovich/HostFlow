/**
 * Type definitions for companies module
 */

export type AnyRecord = Record<string, any>;

export type AddressForm = {
  country?: string;
  city?: string;
  street?: string;
  zip?: string;
  house?: string;
  apartment?: string;
  region?: string;
};

export interface RepresentativeForm {
  full_name: string;
  role?: string;
  id_number?: string;
}

export interface ContactForm {
  role?: string;
  full_name?: string;
  email?: string;
  phone?: string;
  is_primary?: boolean;
  is_portal_user?: boolean;
}

export interface BankAccountForm {
  bank_name?: string;
  account_number?: string;
  swift?: string;
  currency?: string;
  is_default?: boolean;
}

export interface PortalUserForm {
  email: string;
  role?: string;
  permissions?: string;
}

export interface WebhookForm {
  url: string;
  events?: string[];
  secret?: string;
}

export interface ContractForm {
  type?: string;
  start_date?: string;
  end_date?: string;
  amount?: string;
  currency?: string;
  status?: string;
}

export interface OrderFormFieldSchema {
  key: string;
  labelKey: string;
  type: 'string' | 'number';
}

export const ORDER_TYPE_OPTIONS = [
  {
    id: 'transport',
    labelKey: 'app.companies.order_types.transport',
    schema: [
      { key: 'required_drivers', labelKey: 'app.companies.detail.fields.required_drivers', type: 'number' as const },
      { key: 'hired_drivers', labelKey: 'app.companies.detail.fields.hired_drivers', type: 'number' as const },
    ],
  },
  {
    id: 'office',
    labelKey: 'app.companies.order_types.office',
    schema: [
      { key: 'headcount', labelKey: 'app.companies.order_types.fields.headcount', type: 'number' as const },
      { key: 'hired_count', labelKey: 'app.companies.order_types.fields.hired_count', type: 'number' as const },
      { key: 'position_type', labelKey: 'app.companies.order_types.fields.position_type', type: 'string' as const },
    ],
  },
  {
    id: 'production',
    labelKey: 'app.companies.order_types.production',
    schema: [
      { key: 'quantity', labelKey: 'app.companies.order_types.fields.quantity', type: 'number' as const },
      { key: 'delivered', labelKey: 'app.companies.order_types.fields.delivered', type: 'number' as const },
      { key: 'unit', labelKey: 'app.companies.order_types.fields.unit', type: 'string' as const },
    ],
  },
] as const;

export type OrderTypeId = (typeof ORDER_TYPE_OPTIONS)[number]['id'];

export interface OrderForm {
  title?: string;
  status?: string;
  starts_at?: string;
  ends_at?: string;
  required_drivers?: string;
  hired_drivers?: string;
  client_reference?: string;
  code?: string;
  order_type_id?: OrderTypeId | string;
  custom_fields?: Record<string, string | number>;
}

export interface EInvoiceForm {
  participant_id: string;
  scheme: string;
}

export interface CompanyDetailForm {
  base: {
    name: string;
    legal_name: string;
    company_kind: 'client' | 'counterparty';
    tax_id: string;
    phone: string;
    email: string;
    website: string;
    notes: string;
    is_archived: boolean;
    country_code: string;
    city: string;
    address: string;
  };
  legal: {
    reg_no: string;
    vat_eu: string;
    established_at: string;
    transport_license_number: string;
    insurance_policy_no: string;
    registered_address: AddressForm;
    operational_address: AddressForm;
    authorized_representatives: RepresentativeForm[];
  };
  billing: {
    default_currency: string;
    payment_terms_days: string;
    invoice_email: string;
    billing_address: AddressForm;
    einvoice_peppol: EInvoiceForm;
    bank_accounts: BankAccountForm[];
  };
  contacts: ContactForm[];
  operations: {
    fleet_tractors: string;
    fleet_intl_perc: string;
    fleet_local_perc: string;
    drivers_total: string;
    has_adr_operations: boolean;
    work_modes: string[];
    trailer_types: Record<string, string>;
    lanes: { origins: string[]; destinations: string[] };
    cargo_types: string[];
    languages: string[];
    preferred_nationalities: string[];
    // Office / IT
    team_size: string;
    roles: string;
    tech_stack: string;
    // Custom
    custom_fields: Record<string, string>;
  };
  compliance: {
    fin_check_status: string;
    aml_required: boolean;
    iso9001: boolean;
    doc_valid_until: string;
    last_compliance_check_at: string;
  };
  portal: {
    enabled: boolean;
    url: string;
    last_sync_at: string;
    portal_roles: PortalUserForm[];
    permissions: string;
  };
  integrations: {
    provider_ids: string[];
    webhooks: WebhookForm[];
    branding: { logo_url: string; primary_color: string };
  };
  contracts: ContractForm[];
  orders: OrderForm[];
  rawExtra: AnyRecord;
}

export interface ContactInfo {
  role?: string;
  full_name?: string;
  email?: string;
  phone?: string;
  is_primary?: boolean;
  is_portal_user?: boolean;
}
