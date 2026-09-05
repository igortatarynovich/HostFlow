/**
 * Leftover C-4 Test lead route — diagnostic fold into Mapping.
 * Sample obtain / paste / dry-run live on Mapping. This page does not persist mapping.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CRM_APP_PATHS,
  marketingSourceMappingPath,
} from '../../app/crmAppPaths'
import {
  getMarketingSourceSample,
  listMarketingSources,
  mappingAssessmentCopy,
  mappingContractTone,
  mappingWorkspaceCta,
  type MarketingSourceSample,
  type MarketingSourceSummary,
} from '../../api/marketingSources'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { MarketingWorkspaceNav } from './MarketingWorkspaceNav'

export default function MarketingSourceTestLeadPage() {
  const { t } = useI18n()
  const { sourceId = '' } = useParams<{ sourceId: string }>()

  const [source, setSource] = useState<MarketingSourceSummary | null>(null)
  const [sample, setSample] = useState<MarketingSourceSample | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const load = useCallback(async () => {
    if (!sourceId) return
    setLoading(true)
    setError(null)
    try {
      const [rows, sampleRow] = await Promise.all([
        listMarketingSources(),
        getMarketingSourceSample(sourceId),
      ])
      setSource(rows.find((row) => row.source_id === sourceId) ?? null)
      setSample(sampleRow)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.test_lead.errors.load'),
          t,
        ),
      )
      setSample(null)
    } finally {
      setLoading(false)
    }
  }, [sourceId, t])

  useEffect(() => {
    void load()
  }, [load])

  const mappingHref = useMemo(() => {
    if (source?.mapping_path) return source.mapping_path
    return sourceId
      ? marketingSourceMappingPath(sourceId)
      : CRM_APP_PATHS.marketingSources
  }, [source?.mapping_path, sourceId])

  const title = source?.display_name
    ? t('app.marketing.test_lead.title_named', {
        values: { name: source.display_name },
      })
    : t('app.marketing.test_lead.title')

  return (
    <PageShell data-testid="marketing-source-test-lead-page">
      <PageShellHeader>
        <PageHeader
          title={title}
          subtitle={t('app.marketing.test_lead.subtitle')}
          actions={
            <Link
              to={CRM_APP_PATHS.marketingSources}
              className="btn-secondary btn-sm"
              data-testid="marketing-test-lead-back-sources"
            >
              {t('app.marketing.test_lead.actions.back')}
            </Link>
          }
        />
        <MarketingWorkspaceNav />
      </PageShellHeader>

      {error ? (
        <div data-testid="marketing-test-lead-error">
          <ErrorRecoveryBanner info={error} onRetry={() => void load()} />
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500" data-testid="marketing-test-lead-loading">
          {t('common.loading')}
        </p>
      ) : (
        <div className="space-y-6">
          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-test-lead-workspace"
          >
            <p className="text-sm text-slate-700">
              {t('app.marketing.test_lead.workspace.body')}
            </p>
            <Link
              to={mappingHref}
              className="btn-primary btn-sm mt-3 inline-flex"
              data-testid="marketing-test-lead-continue-mapping"
            >
              {source
                ? mappingWorkspaceCta(source)
                : t('app.marketing.test_lead.workspace.open')}
            </Link>
          </section>

          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-test-lead-context"
          >
            <h2 className="text-sm font-semibold text-slate-900">
              {t('app.marketing.test_lead.context.title')}
            </h2>
            <dl className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.test_lead.context.provider')}
                </dt>
                <dd data-testid="marketing-test-lead-provider">
                  {source?.provider || t('app.marketing.sources.none')}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.test_lead.context.health')}
                </dt>
                <dd
                  className={`font-medium ${source ? mappingContractTone(source.contract_health || source.mapping_health) : ''}`}
                  data-testid="marketing-test-lead-health"
                >
                  {source ? mappingAssessmentCopy(source) : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.test_lead.context.sample_source')}
                </dt>
                <dd data-testid="marketing-test-lead-sample-source">
                  {sample?.sample_source || 'none'}
                </dd>
              </div>
            </dl>
          </section>
        </div>
      )}
    </PageShell>
  )
}
