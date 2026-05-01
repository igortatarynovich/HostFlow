/**
 * Inner content of a pipeline kanban card (below drag handle / checkbox).
 */

import { Link } from 'react-router-dom';
import {
  IconArrowRight,
  IconBriefcase,
  IconCalendar,
  IconFileText,
  IconMail,
  IconMapPin,
  IconPhone,
  IconUser,
} from '@tabler/icons-react';
import type { Vacancy } from '../../api/types';
import { CRM_APP_PATHS } from '../../app/crmAppPaths';
import { useI18n } from '../../i18n';
import type { ManagerItem } from './types';
import { pickMiniFields, telHrefFromDisplay } from './utils';

export type PipelineKanbanCardBodyProps = {
  item: unknown;
  candidateId: string;
  managers: ManagerItem[];
  vacancyId: string;
  vacancies: Vacancy[];
  canViewTasks: boolean;
  shouldSuppressLinkClick: (id: string) => boolean;
};

export function PipelineKanbanCardBody({
  item,
  candidateId,
  managers,
  vacancyId,
  vacancies,
  canViewTasks,
  shouldSuppressLinkClick,
}: PipelineKanbanCardBodyProps) {
  const { t } = useI18n();
  const row = item as Record<string, unknown>;
  const c = (row.candidate as Record<string, unknown>) || row || {};
  const meta = pickMiniFields(item);
  const managerId = (c.manager_id || c.manager || row.manager || row.manager_id) as string | undefined;
  const manager = managers.find((m) => m.id === managerId);
  const vacancyTitle =
    (row.vacancy as { title?: string } | undefined)?.title ||
    (row.vacancy_title as string | undefined) ||
    (vacancies.find((v) => v.id === vacancyId) as { title?: string } | undefined)?.title;
  const createdDate = (c.created_at as string | undefined) || (row.created_at as string | undefined);
  const formattedDate = createdDate
    ? new Date(createdDate).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
    : null;
  const cand = row.candidate as Record<string, unknown> | undefined;
  const emailRaw = String(c.email || cand?.email || row.candidate_email || '').trim();
  const telHref = telHrefFromDisplay(meta.phone as string | null | undefined);
  const cardHref = CRM_APP_PATHS.candidates + '/' + candidateId;
  const taskLabel = String(cand?.name || row.candidate_name || candidateId).slice(0, 80);
  const tasksHref =
    CRM_APP_PATHS.tasks +
    '?tab=tasks&t_status=active&t_entity=candidate&t_q=' +
    encodeURIComponent(taskLabel);
  const actionBtnClass =
    'inline-flex items-center gap-0.5 rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-800 shadow-sm hover:border-brand-300 hover:bg-brand-50/80';

  const displayName =
    (cand?.name as string | undefined) ||
    (row.candidate_name as string | undefined) ||
    t('app.candidates.pipeline.candidate_no_name');

  return (
    <div className="mt-1">
      <div className="font-medium">
        <Link
          className="hover:underline"
          to={cardHref}
          onClick={(evt) => {
            if (shouldSuppressLinkClick(candidateId)) {
              evt.preventDefault();
              evt.stopPropagation();
            }
          }}
        >
          {displayName}
        </Link>
      </div>
      <div className="text-xs text-slate-500 mb-2">{emailRaw || '—'}</div>
      <div className="text-xs text-slate-600 space-y-1">
        {meta.phone ? (
          <div className="inline-flex items-center gap-1">
            <IconPhone size={12} /> {meta.phone}
          </div>
        ) : null}
        {meta.citizenship ? (
          <div className="inline-flex items-center gap-1">
            <IconMapPin size={12} /> {meta.citizenship}
          </div>
        ) : null}
        {manager ? (
          <div className="inline-flex items-center gap-1">
            <IconUser size={12} /> {manager.name}
          </div>
        ) : null}
        {vacancyTitle && vacancyId && vacancies.length > 1 ? (
          <div className="inline-flex items-center gap-1">
            <IconBriefcase size={12} /> {vacancyTitle}
          </div>
        ) : null}
        {formattedDate ? (
          <div className="inline-flex items-center gap-1">
            <IconCalendar size={12} /> {formattedDate}
          </div>
        ) : null}
        {meta.docsBadge ? (
          <div className="inline-flex items-center gap-1">
            <IconFileText size={12} /> {t('app.candidates.pipeline.docs_label')}: {meta.docsBadge}
          </div>
        ) : null}
      </div>
      <div
        className="mt-2 flex flex-wrap gap-1 border-t border-slate-100 pt-2"
        onPointerDown={(e) => e.stopPropagation()}
      >
        {telHref ? (
          <a href={telHref} className={actionBtnClass}>
            <IconPhone size={11} stroke={2} className="shrink-0 text-slate-600" aria-hidden />
            {t('app.candidates.pipeline.action_call', { defaultValue: 'Call' })}
          </a>
        ) : null}
        {emailRaw ? (
          <a href={'mailto:' + emailRaw} className={actionBtnClass}>
            <IconMail size={11} stroke={2} className="shrink-0 text-slate-600" aria-hidden />
            {t('app.candidates.pipeline.action_write', { defaultValue: 'Email' })}
          </a>
        ) : null}
        <Link
          to={cardHref}
          className={actionBtnClass}
          onClick={(evt) => {
            if (shouldSuppressLinkClick(candidateId)) {
              evt.preventDefault();
              evt.stopPropagation();
            }
          }}
        >
          <IconArrowRight size={11} stroke={2} className="shrink-0 text-slate-600" aria-hidden />
          {t('app.candidates.pipeline.action_open_card', { defaultValue: 'Open' })}
        </Link>
        {canViewTasks ? (
          <Link to={tasksHref} className={actionBtnClass}>
            {t('app.candidates.pipeline.action_tasks', { defaultValue: 'Tasks' })}
          </Link>
        ) : null}
      </div>
    </div>
  );
}
