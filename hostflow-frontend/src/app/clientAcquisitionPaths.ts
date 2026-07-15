import { CRM_APP_PATHS } from './crmAppPaths'

export function clientAcquisitionChannelPath(channelId: string): string {
  return `${CRM_APP_PATHS.clientAcquisitionChannels}/${encodeURIComponent(channelId)}`
}

export function clientAcquisitionInquiryPath(channelId: string, leadId: string): string {
  return `${clientAcquisitionChannelPath(channelId)}/inquiries/${encodeURIComponent(leadId)}`
}
