/**
 * Type definitions for candidate card module
 */

export type Tab = 'personal' | 'docs' | 'services' | 'timeline';
export type PreferredContact = 'viber' | 'whatsapp' | 'telegram' | 'phone' | '';
export type Option = { value: string; label: string; extra?: any };
export type AddressFields = {
  country: string;
  city: string;
  street: string;
  house: string;
  apt: string;
  zip: string;
};

export type CandidateNote = {
  id: string;
  text: string;
  visibility: 'internal' | 'client' | 'candidate';
  author_id: string;
  created_at: string;
};

export type StageHistoryEntry = {
  id: string;
  from_code: string | null;
  to_code: string | null;
  at: string | null;
  actor: string | null;
  reason: string | null;
};

