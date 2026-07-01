/**
 * Type definitions for tenants module
 */

import type { TenantLicense, TenantStatus, TenantType } from '../../api/types';
import type { LicenseFormState } from './utils';

export type StatusFilter = 'all' | TenantStatus;
export type TypeFilter = 'all' | TenantType;

export type CreateTenantForm = {
  name: string;
  slug: string;
  workspace_label: string;
  type: TenantType;
  status: TenantStatus;
  client_portal_enabled: boolean;
  status_sharing_allowed: boolean;
  license: LicenseFormState;
  initial_admin_email: string;
  initial_admin_name: string;
  initial_admin_password: string;
};

