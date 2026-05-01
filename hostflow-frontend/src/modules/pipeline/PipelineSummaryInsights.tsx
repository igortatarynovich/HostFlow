/**
 * Sidebar insights strip for Pipeline (kanban metrics).
 */

import { useI18n } from '../../i18n';
import type { PipelineColumnInsights } from './filterPipelineColumns';

export function PipelineSummaryInsights({ insights }: { insights: PipelineColumnInsights }) {
  const { t } = useI18n();
  const cards = [
    {
      label: t('app.candidates.insights.total'),
      value: insights.total,
      hint: t('app.candidates.insights.total_hint', { values: { count: insights.total } }),
    },
    {
      label: t('app.candidates.insights.new'),
      value: insights.newCount,
      hint: t('app.candidates.insights.new_hint', { values: { count: insights.newCount } }),
    },
    {
      label: t('app.candidates.insights.docs_ready'),
      value: insights.docsReady,
      hint: t('app.candidates.insights.docs_ready_hint', { values: { count: insights.docsReady } }),
    },
    {
      label: t('app.candidates.insights.docs_attention'),
      value: insights.docsAttention,
      hint: t('app.candidates.insights.docs_attention_hint', { values: { count: insights.docsAttention } }),
    },
  ];

  return (
    <section className="rounded-xl bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 p-3 text-white shadow-sm">
      <div className="flex flex-col gap-2">
        <h2 className="text-sm font-bold">{t('app.candidates.insights.title')}</h2>
        <p className="text-[10px] text-white/80 leading-tight">{t('app.candidates.insights.subtitle')}</p>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-white/30 bg-white/10 px-2 py-1.5 shadow-inner backdrop-blur"
          >
            <div className="text-[9px] uppercase tracking-wide text-white/80 leading-tight">{card.label}</div>
            <div className="text-lg font-semibold leading-tight">{card.value}</div>
            <div className="text-[9px] text-white/70 leading-tight mt-0.5">{card.hint}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
