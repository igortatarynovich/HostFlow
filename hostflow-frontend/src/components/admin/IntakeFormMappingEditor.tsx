import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { marketingSourceMappingPath } from '../../app/crmAppPaths'
import { getIntakeFormMapping } from '../../api/intakeForms'

type Props = {
  formId: string
}

export function IntakeFormMappingEditor({ formId }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const [loading, setLoading] = useState(true)
  const [workspaceSourceId, setWorkspaceSourceId] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!formId) return
    setLoading(true)
    try {
      const ctx = await getIntakeFormMapping(formId)
      setWorkspaceSourceId(ctx.intake_source_profile_id)
    } catch {
      setWorkspaceSourceId(null)
      notify({
        title: t('admin.intake_forms.errors.load_mapping', { defaultValue: 'Failed to load mapping' }),
        variant: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [formId, notify, t])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading')}</p>
  }

  if (workspaceSourceId) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm" data-testid="intake-form-mapping-workspace">
        <p className="text-slate-700">
          {t('admin.intake_forms.mapping_workspace.body', {
            defaultValue: 'Edit mapping for this form in the Mapping workspace — one editor for every intake source.',
          })}
        </p>
        <Link
          className="btn-primary btn-sm mt-3 inline-flex"
          to={marketingSourceMappingPath(workspaceSourceId)}
        >
          {t('admin.intake_forms.mapping_workspace.open', { defaultValue: 'Open mapping' })}
        </Link>
      </div>
    )
  }

  return (
    <div
      className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-950"
      data-testid="intake-form-mapping-unbound"
    >
      {t('admin.intake_forms.mapping_workspace.unbound', {
        defaultValue: 'This form is not bound to an intake source. Mapping cannot be edited here.',
      })}
    </div>
  )
}
