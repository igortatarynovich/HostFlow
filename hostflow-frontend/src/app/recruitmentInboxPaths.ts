import { CRM_APP_PATHS } from './crmAppPaths'

/** Recruitment Application Workspace — UI Constitution v1. No Lead in UI. */
export const RECRUITMENT_INBOX_PATH = `${CRM_APP_PATHS.appShellPrefix}/recruitment/inbox`

export function recruitmentApplicationPath(applicationId: string): string {
  return `${RECRUITMENT_INBOX_PATH}/${encodeURIComponent(applicationId)}`
}

/** @deprecated Use recruitmentApplicationPath — Lead routes removed from product surface. */
export function recruitmentLeadWorkPath(applicationId: string): string {
  return recruitmentApplicationPath(applicationId)
}
