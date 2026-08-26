import api from './client'

export type DisplayCurrency = 'USD' | 'PLN' | 'EUR'

export type FxRatesResponse = {
  as_of: string
  provider: string
  base: string
  supported: string[]
  pln_per_unit: Record<string, string>
  /** rates[from][to] = units of `to` per 1 `from` */
  rates: Record<string, Record<string, string>>
}

const DISPLAY_CURRENCIES: DisplayCurrency[] = ['USD', 'PLN', 'EUR']

export function isDisplayCurrency(value: string | null | undefined): value is DisplayCurrency {
  const v = String(value || '').trim().toUpperCase()
  return DISPLAY_CURRENCIES.includes(v as DisplayCurrency)
}

export async function getFxRates(refresh = false): Promise<FxRatesResponse> {
  const { data } = await api.get<FxRatesResponse>('/fx/rates', {
    params: refresh ? { refresh: true } : undefined,
  })
  return data
}

/** Convert using matrix from GET /fx/rates (NBP mid via PLN). */
export function convertWithRates(
  amount: number,
  fromCurrency: string,
  toCurrency: string,
  rates: FxRatesResponse | null,
): number {
  const src = String(fromCurrency || '').trim().toUpperCase()
  const dst = String(toCurrency || '').trim().toUpperCase()
  if (!Number.isFinite(amount)) return 0
  if (src === dst) return amount
  const quote = rates?.rates?.[src]?.[dst]
  if (quote == null || quote === '') return amount
  const rate = Number(String(quote).replace(',', '.'))
  if (!Number.isFinite(rate)) return amount
  return amount * rate
}

export { DISPLAY_CURRENCIES }
