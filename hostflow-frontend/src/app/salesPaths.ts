import { CRM_APP_PATHS } from './crmAppPaths'

/** Channel-independent Sales entry ("Что дальше" + work session over company inquiries). */
export const SALES_HOME_PATH = `${CRM_APP_PATHS.appShellPrefix}/sales`

/** ADR-032 Sales Service Orders list (not Services-module `/app/orders`). */
export const SALES_ORDERS_PATH = CRM_APP_PATHS.salesOrders

/** Channel-independent inquiry work card path. */
export function salesInquiryPath(inquiryId: string): string {
  return `${SALES_HOME_PATH}/inquiries/${encodeURIComponent(inquiryId)}`
}

/** Sales Service Order detail. */
export function salesOrderPath(orderId: string): string {
  return `${SALES_ORDERS_PATH}/${encodeURIComponent(orderId)}`
}

/** Create form for a new Sales Service Order. */
export function salesOrderNewPath(): string {
  return `${SALES_ORDERS_PATH}/new`
}

/** Parse a SalesInquiry id (or legacy Lead id) out of a Sales inquiry path. */
export function parseSalesHomeInquiryId(pathname: string): string | null {
  const marker = '/sales/inquiries/'
  const idx = pathname.indexOf(marker)
  if (idx < 0) return null
  const rest = pathname.slice(idx + marker.length)
  const id = rest.split('/')[0]?.split('?')[0]
  return id || null
}

/** @deprecated Use parseSalesHomeInquiryId — queue ids are SalesInquiry ids. */
export const parseSalesHomeInquiryLeadId = parseSalesHomeInquiryId
