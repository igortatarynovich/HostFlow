import type { FormDefinitionLike } from '../../utils/intakeFormRoutingSummary'
import {
  answersDestinationLabel,
  entityProfileLabel,
  managerDecisionLabel,
  personalInviteBehaviorLabel,
  publicSubmitBehaviorLabel,
  purposeLabel,
  purposeLabelKey,
  salesInboxPath,
  salesModuleLabel,
} from '../../utils/intakeFormRoutingSummary'
import { intakePresentationProfileTitle } from '../../utils/intakePresentationI18n'
import { useI18n } from '../../i18n'

type Props = {
  definition: FormDefinitionLike | null | undefined
  entityProfileCode?: string | null
  entityProfileName?: string | null
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-slate-100 py-2 last:border-0 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-sm font-medium text-slate-900 sm:max-w-[65%] sm:text-right">{value}</dd>
    </div>
  )
}

export default function IntakeFormAnswersRoutingCard({ definition, entityProfileCode, entityProfileName }: Props) {
  const { t, locale } = useI18n()
  const profileCode = entityProfileCode || definition?.target_entity_profile_code || ''
  const profileName =
    entityProfileName ||
    intakePresentationProfileTitle(
      t,
      { entity_profile_code: profileCode, profile_name: entityProfileLabel(profileCode) },
      locale,
    )

  return (
    <section className="rounded-xl border border-brand-100 bg-brand-50/30 p-4" data-testid="intake-form-routing-card">
      <h3 className="text-sm font-semibold text-slate-900">
        {t('admin.intake_forms.sections.answers_routing', { defaultValue: 'Where answers go' })}
      </h3>
      <p className="mt-1 text-xs text-slate-600">
        {t('admin.intake_forms.answers_routing_hint', {
          defaultValue: 'Plain-language routing for operators. No internal policy codes.',
        })}
      </p>
      <dl className="mt-3">
        <Row
          label={t('admin.intake_forms.routing.purpose', { defaultValue: 'Purpose' })}
          value={t(purposeLabelKey(definition?.purpose), { defaultValue: purposeLabel(definition?.purpose) })}
        />
        <Row label={t('admin.intake_forms.routing.profile', { defaultValue: 'Profile' })} value={profileName} />
        <Row
          label={t('admin.intake_forms.routing.module', { defaultValue: 'Module' })}
          value={salesModuleLabel(profileCode)}
        />
        <Row
          label={t('admin.intake_forms.routing.inbox', { defaultValue: 'Inbox' })}
          value={salesInboxPath(profileCode)}
        />
        <Row
          label={t('admin.intake_forms.routing.public_submit', { defaultValue: 'Public link submit' })}
          value={publicSubmitBehaviorLabel(definition)}
        />
        <Row
          label={t('admin.intake_forms.routing.personal_invite', { defaultValue: 'Send from inquiry' })}
          value={personalInviteBehaviorLabel()}
        />
        <Row
          label={t('admin.intake_forms.routing.answers', { defaultValue: 'Answers stored as' })}
          value={answersDestinationLabel(profileCode)}
        />
        <Row
          label={t('admin.intake_forms.routing.next_decision', { defaultValue: 'Manager can then' })}
          value={managerDecisionLabel(profileCode)}
        />
      </dl>
      <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-slate-700">
        <li>
          {t('admin.intake_forms.routing.summary_public', {
            defaultValue: 'After public fill: Sales → Inquiries',
          })}
        </li>
        <li>
          {t('admin.intake_forms.routing.summary_invite', {
            defaultValue: 'When sent from an inquiry: answers attach to that inquiry',
          })}
        </li>
      </ul>
    </section>
  )
}
