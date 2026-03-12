/**
 * Type definitions for services module
 */

export type NewServiceFormState = {
  code: string;
  name: string;
  category: string;
  basePrice: string;
  vatRate: string;
  resultDocumentType: string;
  requiresSchedule: boolean;
  requiresCandidate: boolean;
};

export type NewOrderFormState = {
  candidateId: string;
  vacancyId: string;
  companyId: string;
  notes: string;
  serviceId: string;
  serviceCode: string;
  qty: string;
  unitPrice: string;
  vatRate: string;
  currency: string;
};

