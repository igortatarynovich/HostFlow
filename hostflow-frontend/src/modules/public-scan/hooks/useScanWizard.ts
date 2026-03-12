import { useMemo } from 'react'
import type { ScanSession, ScanPage } from '@api/scanner'
import { getScannerPreset } from '@modules/scannerPresets'
import type { TranslateFn } from '@i18n'

const READY_STATUSES: Array<ScanPage['status']> = ['ok', 'needs_review', 'uploaded', 'done']

export function isReadyPage(page?: ScanPage): boolean {
  if (!page) return false
  return READY_STATUSES.includes(page.status)
}

export function useScanWizard(
  session: ScanSession | null,
  presetStepCodes: string[],
  preset: ReturnType<typeof getScannerPreset>,
  translate: TranslateFn,
  statusBadgeTone: (status: string) => string
) {
  const stepMeta = useMemo(() => {
    const map = new Map<string, { optional: boolean; label: string }>()
    preset?.steps?.forEach((step) => {
      map.set(step.code, { optional: Boolean(step.optional), label: step.label })
    })
    return map
  }, [preset])

  const orderedStepCodes = session?.expected_pages?.length ? session.expected_pages : presetStepCodes

  const wizardSteps = useMemo(() => {
    return orderedStepCodes.map((code, index) => {
      const page = session?.pages?.find((p) => p.page_code === code)
      const meta = stepMeta.get(code)
      return {
        code,
        index,
        optional: meta?.optional ?? false,
        label: translate(`public.scan.pages.${code}`, meta?.label ?? code),
        page,
      }
    })
  }, [orderedStepCodes, session?.pages, stepMeta, translate])

  const formatStepStatus = (statusKey?: string | null) => {
    const key = statusKey ?? 'pending'
    return {
      key,
      text: translate(`public.scan.status.${key}`, key),
      tone: statusBadgeTone(key),
    }
  }

  const requiredSteps = wizardSteps.filter((step) => !step.optional)
  const canProcess =
    wizardSteps.length > 0 &&
    (requiredSteps.length > 0
      ? requiredSteps.every((step) => isReadyPage(step.page))
      : wizardSteps.every((step) => isReadyPage(step.page)))

  const allPagesComplete =
    wizardSteps.length > 0 && wizardSteps.every((step) => isReadyPage(step.page) || step.optional)

  const firstBlockingStep = wizardSteps.find((step) => !isReadyPage(step.page) && !step.optional)
  const firstPendingStep = wizardSteps.find((step) => !isReadyPage(step.page))

  return {
    wizardSteps,
    formatStepStatus,
    canProcess,
    allPagesComplete,
    firstBlockingStep,
    firstPendingStep,
    requiredSteps,
  }
}

