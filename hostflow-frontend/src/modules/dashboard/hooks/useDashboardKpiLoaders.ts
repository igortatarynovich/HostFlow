import { useCallback, useEffect, useState } from 'react'
import { listInvoices } from '../../../api/client'
import {
  getOpsCounters,
  getStageMetrics,
  type OpsCounters,
  type StageMetricsResponse,
} from '../../../api/analytics'
import { listVacancies } from '../../../api/vacancies'
import { invoiceDaysPastDue, invoiceOutstandingAmount } from '../../services/utils'
import type { InvoiceWithPaid } from '../internal'

export interface InvoiceMoneySummary {
  totalOutstanding: number
  overdueUnpaidCount: number
  maxDaysPastDue: number | null
  currency: string
}

export interface VacanciesOpenSummary {
  openCount: number
  candidatesInOpen: number
  capped: boolean
}

export interface UseDashboardKpiLoadersOptions {
  canVacanciesOpenWidget: boolean
  canServicesOpsWidgets: boolean
}

export interface UseDashboardKpiLoadersResult {
  opsCounters: OpsCounters | null
  opsCountersLoading: boolean
  vacanciesOpenLoading: boolean
  vacanciesOpenSummary: VacanciesOpenSummary | null
  invoiceMoney: InvoiceMoneySummary | null
  invoiceMoneyLoading: boolean
  stageMetrics: StageMetricsResponse | null
  stageMetricsLoading: boolean
  loadOpsCounters: () => Promise<void>
  loadInvoiceMoneyWidget: () => Promise<void>
  loadStageMetrics: () => Promise<void>
}

/**
 * Encapsulates three independent loaders + state slices used by `pages/Dashboard.tsx`:
 * - Ops counters (+ open-vacancies fallback fetch)
 * - Invoice money summary (totalOutstanding, overdue, maxDaysPastDue, currency)
 * - Stage metrics (transitions snapshot)
 *
 * Each loader is wired to its own auto-load `useEffect` so the page only needs
 * to read the resulting state and call the loaders for manual refresh.
 */
export function useDashboardKpiLoaders({
  canVacanciesOpenWidget,
  canServicesOpsWidgets,
}: UseDashboardKpiLoadersOptions): UseDashboardKpiLoadersResult {
  const [opsCounters, setOpsCounters] = useState<OpsCounters | null>(null)
  const [opsCountersLoading, setOpsCountersLoading] = useState(false)
  const [vacanciesOpenLoading, setVacanciesOpenLoading] = useState(false)
  const [vacanciesOpenSummary, setVacanciesOpenSummary] =
    useState<VacanciesOpenSummary | null>(null)
  const [invoiceMoney, setInvoiceMoney] = useState<InvoiceMoneySummary | null>(null)
  const [invoiceMoneyLoading, setInvoiceMoneyLoading] = useState(false)
  const [stageMetrics, setStageMetrics] = useState<StageMetricsResponse | null>(null)
  const [stageMetricsLoading, setStageMetricsLoading] = useState(false)

  const loadOpsCounters = useCallback(async () => {
    setOpsCountersLoading(true)
    if (canVacanciesOpenWidget) setVacanciesOpenLoading(true)
    try {
      const data = await getOpsCounters()
      setOpsCounters(data)
      if (canVacanciesOpenWidget) {
        if (typeof data.open_vacancies === 'number') {
          setVacanciesOpenSummary({
            openCount: data.open_vacancies,
            candidatesInOpen:
              typeof data.open_vacancies_candidates === 'number'
                ? data.open_vacancies_candidates
                : 0,
            capped: false,
          })
        } else {
          try {
            const rows = await listVacancies({ status: 'open', limit: 200 })
            const list = Array.isArray(rows) ? rows : []
            const capped = list.length >= 200
            let candidatesInOpen = 0
            for (const v of list) {
              candidatesInOpen += Number(v.candidate_count || 0)
            }
            setVacanciesOpenSummary({ openCount: list.length, candidatesInOpen, capped })
          } catch {
            setVacanciesOpenSummary(null)
          }
        }
      }
    } catch {
      setOpsCounters(null)
      if (canVacanciesOpenWidget) setVacanciesOpenSummary(null)
    } finally {
      setOpsCountersLoading(false)
      if (canVacanciesOpenWidget) setVacanciesOpenLoading(false)
    }
  }, [canVacanciesOpenWidget])

  useEffect(() => {
    void loadOpsCounters()
  }, [loadOpsCounters])

  const loadInvoiceMoneyWidget = useCallback(async () => {
    if (!canServicesOpsWidgets) return
    setInvoiceMoneyLoading(true)
    try {
      const data = await listInvoices({ limit: 200 })
      const rows = Array.isArray(data) ? (data as InvoiceWithPaid[]) : []
      let totalOutstanding = 0
      let overdueUnpaidCount = 0
      let maxDaysPastDue: number | null = null
      let currency = 'PLN'
      for (const inv of rows) {
        const st = String(inv.status || '').toLowerCase()
        if (st === 'cancelled' || st === 'paid') continue
        const out = invoiceOutstandingAmount(inv.total_amount, inv.paid_amount)
        if (out <= 0) continue
        currency = inv.currency || currency
        totalOutstanding += out
        const days = invoiceDaysPastDue(inv.due_date, out)
        if (days != null) {
          maxDaysPastDue = maxDaysPastDue == null ? days : Math.max(maxDaysPastDue, days)
        }
        if (
          inv.status === 'overdue' &&
          Number(inv.total_amount || 0) > Number(inv.paid_amount || 0)
        ) {
          overdueUnpaidCount += 1
        }
      }
      setInvoiceMoney({ totalOutstanding, overdueUnpaidCount, maxDaysPastDue, currency })
    } catch {
      setInvoiceMoney(null)
    } finally {
      setInvoiceMoneyLoading(false)
    }
  }, [canServicesOpsWidgets])

  useEffect(() => {
    void loadInvoiceMoneyWidget()
  }, [loadInvoiceMoneyWidget])

  const loadStageMetrics = useCallback(async () => {
    setStageMetricsLoading(true)
    try {
      const data = await getStageMetrics({ limit_transitions: 12 })
      setStageMetrics(data)
    } catch {
      setStageMetrics(null)
    } finally {
      setStageMetricsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadStageMetrics()
  }, [loadStageMetrics])

  return {
    opsCounters,
    opsCountersLoading,
    vacanciesOpenLoading,
    vacanciesOpenSummary,
    invoiceMoney,
    invoiceMoneyLoading,
    stageMetrics,
    stageMetricsLoading,
    loadOpsCounters,
    loadInvoiceMoneyWidget,
    loadStageMetrics,
  }
}
