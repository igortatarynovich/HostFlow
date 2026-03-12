/**
 * Utility functions for services module
 */

const currency = new Intl.NumberFormat('pl-PL', {
  style: 'currency',
  currency: 'PLN',
});

export function formatAmount(value: number | null | undefined, fallback = '-'): string {
  if (value == null || Number.isNaN(value)) {
    return fallback;
  }
  try {
    return currency.format(value);
  } catch (err) {
    return value.toFixed(2);
  }
}

