/**
 * Type definitions for services module
 */

export type NewServiceFormState = {
  code: string;
  name: string;
  category: string;
  basePrice: string;
  estimatedCost: string;
  costCurrency: string;
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
  estimatedCost: string;
  actualCost: string;
  costCurrency: string;
  vatRate: string;
  currency: string;
};
