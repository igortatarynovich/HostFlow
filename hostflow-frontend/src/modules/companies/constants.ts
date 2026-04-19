/**
 * Constants for companies module
 */

export const ENABLE_READINESS = true; // readiness API enabled

export type StatusTone = 'info' | 'success' | 'warning' | 'danger';

export const READINESS_STATE_META: Record<string, { labelKey: string; tone: StatusTone }> = {
  ready: { labelKey: 'app.companies.readiness.states.ready', tone: 'success' },
  legal_missing: { labelKey: 'app.companies.readiness.states.legal_missing', tone: 'warning' },
  contact_missing: { labelKey: 'app.companies.readiness.states.contact_missing', tone: 'warning' },
  bank_missing: { labelKey: 'app.companies.readiness.states.bank_missing', tone: 'warning' },
  billing_invalid: { labelKey: 'app.companies.readiness.states.billing_invalid', tone: 'warning' },
  compliance_expired: { labelKey: 'app.companies.readiness.states.compliance_expired', tone: 'danger' },
};

export const FIN_STATUS_LABELS: Record<string, string> = {
  pending: 'app.companies.readiness.fin_status.pending',
  pass: 'app.companies.readiness.fin_status.pass',
  fail: 'app.companies.readiness.fin_status.fail',
  manual_review: 'app.companies.readiness.fin_status.manual_review',
};

export const CURRENCY_OPTIONS = ['PLN', 'EUR', 'USD', 'GBP'];
export const FIN_STATUS_OPTIONS = ['pending', 'pass', 'fail', 'manual_review'];
export const CONTACT_ROLE_OPTIONS = ['OWNER', 'ACC', 'HR', 'FM', 'OPS', 'LEGAL', 'DISPATCH', 'SALES', 'SUPPORT', 'CEO'];
export const CONTACT_ROLE_SET = new Set(CONTACT_ROLE_OPTIONS);
export const CONTACT_ROLE_ALIASES: Record<string, string> = {
  ACCOUNTING: 'ACC',
  ACCOUNTANT: 'ACC',
  ACCOUNTS: 'ACC',
  MAIN: 'OWNER',
  OPERATIONS: 'OPS',
  OPERATION: 'OPS',
  DISPATCHER: 'DISPATCH',
  CUSTOMER_SUPPORT: 'SUPPORT',
  CUSTOMER_SERVICE: 'SUPPORT',
  SUPPORT_TEAM: 'SUPPORT',
  SALES_MANAGER: 'SALES',
  SALES_TEAM: 'SALES',
  FINANCE: 'FM',
  FINANCIAL: 'FM',
  FINANCIAL_MANAGER: 'FM',
  FINANCE_MANAGER: 'FM',
};
export const WORK_MODE_OPTIONS = ['UOP', 'B2B', 'LEASE'];
export const TRAILER_TYPE_KEYS = ['mega', 'standard', 'frigo', 'container'];

