import {
  IconCopy,
  IconEdit,
  IconExternalLink,
  IconEye,
  IconSend,
} from '@tabler/icons-react'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { SALES_HOME_PATH } from '../../app/salesPaths'
import { salesInboxPath } from '../../utils/intakeFormRoutingSummary'

type Props = {
  title: string
  capabilityLabel?: string
  isActive: boolean
  publicUrl: string
  entityProfileCode: string
  onCopyLink: () => void
  onEditQuestions: () => void
}

export function QuestionnaireCard({
  title,
  capabilityLabel,
  isActive,
  publicUrl,
  entityProfileCode,
  onCopyLink,
  onEditQuestions,
}: Props) {
  const { t } = useI18n()
  const salesPath = entityProfileCode.startsWith('service_sales.') ? SALES_HOME_PATH : salesInboxPath(entityProfileCode)

  const actions = [
    {
      key: 'send',
      label: t('admin.questionnaire_card.send', { defaultValue: 'Отправить клиенту' }),
      hint: t('admin.questionnaire_card.send_hint', {
        defaultValue: 'Откройте обращение в Sales и отправьте персональную ссылку.',
      }),
      icon: IconSend,
      render: () => (
        <Link to={salesPath} className="questionnaire-card-action">
          <IconSend size={22} stroke={1.8} />
          <span>{t('admin.questionnaire_card.send', { defaultValue: 'Отправить клиенту' })}</span>
        </Link>
      ),
    },
    {
      key: 'open',
      label: t('admin.questionnaire_card.open_public', { defaultValue: 'Открыть публичную форму' }),
      icon: IconExternalLink,
      render: () =>
        publicUrl ? (
          <a href={publicUrl} target="_blank" rel="noreferrer" className="questionnaire-card-action">
            <IconExternalLink size={22} stroke={1.8} />
            <span>{t('admin.questionnaire_card.open_public', { defaultValue: 'Открыть публичную форму' })}</span>
          </a>
        ) : null,
    },
    {
      key: 'copy',
      label: t('admin.questionnaire_card.copy_link', { defaultValue: 'Скопировать ссылку' }),
      icon: IconCopy,
      render: () => (
        <button type="button" className="questionnaire-card-action" disabled={!publicUrl} onClick={onCopyLink}>
          <IconCopy size={22} stroke={1.8} />
          <span>{t('admin.questionnaire_card.copy_link', { defaultValue: 'Скопировать ссылку' })}</span>
        </button>
      ),
    },
    {
      key: 'preview',
      label: t('admin.questionnaire_card.preview', { defaultValue: 'Предпросмотр' }),
      icon: IconEye,
      render: () =>
        publicUrl ? (
          <a href={publicUrl} target="_blank" rel="noreferrer" className="questionnaire-card-action">
            <IconEye size={22} stroke={1.8} />
            <span>{t('admin.questionnaire_card.preview', { defaultValue: 'Предпросмотр' })}</span>
          </a>
        ) : null,
    },
    {
      key: 'edit',
      label: t('admin.questionnaire_card.edit_questions', { defaultValue: 'Редактировать вопросы' }),
      icon: IconEdit,
      render: () => (
        <button type="button" className="questionnaire-card-action" onClick={onEditQuestions}>
          <IconEdit size={22} stroke={1.8} />
          <span>{t('admin.questionnaire_card.edit_questions', { defaultValue: 'Редактировать вопросы' })}</span>
        </button>
      ),
    },
  ]

  return (
    <div className="rounded-2xl border border-brand-100 bg-white p-6 shadow-sm" data-testid="questionnaire-card">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-slate-900">
          {t('admin.questionnaire_card.title_prefix', { defaultValue: 'Анкета «{{title}}»', values: { title } })}
        </h2>
        {capabilityLabel ? (
          <p className="text-sm text-slate-600">
            {t('admin.questionnaire_card.direction', {
              defaultValue: 'Направление: {{label}}',
              values: { label: capabilityLabel },
            })}
          </p>
        ) : null}
        <p className="text-sm font-medium text-emerald-700">
          {isActive
            ? t('admin.questionnaire_card.status_active', { defaultValue: 'Статус: Активна' })
            : t('admin.questionnaire_card.status_inactive', { defaultValue: 'Статус: Неактивна' })}
        </p>
      </div>

      <div
        className="mt-5 space-y-2 rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-sm text-slate-700"
        data-testid="questionnaire-card-usage-copy"
      >
        <p>
          {t('admin.questionnaire_card.usage_from_inquiry', {
            defaultValue:
              'Если отправить из заявки в Sales — ответы попадут именно в эту заявку.',
          })}
        </p>
        <p>
          {t('admin.questionnaire_card.usage_public_link', {
            defaultValue:
              'Если использовать публичную ссылку — система найдёт подходящую заявку или создаст новую.',
          })}
        </p>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {actions.map((action) => {
          const node = action.render()
          if (!node) return null
          return (
            <div key={action.key} className="min-w-0">
              {node}
            </div>
          )
        })}
      </div>

      <style>{`
        .questionnaire-card-action {
          display: flex;
          width: 100%;
          min-height: 4.5rem;
          align-items: center;
          gap: 0.75rem;
          border-radius: 1rem;
          border: 1px solid rgb(226 232 240);
          background: rgb(248 250 252 / 0.8);
          padding: 1rem 1.25rem;
          text-align: left;
          font-size: 0.95rem;
          font-weight: 600;
          color: rgb(15 23 42);
          transition: border-color 0.15s ease, background 0.15s ease;
        }
        .questionnaire-card-action:hover:not(:disabled) {
          border-color: rgb(147 197 253);
          background: rgb(239 246 255 / 0.9);
        }
        .questionnaire-card-action:disabled {
          cursor: not-allowed;
          opacity: 0.5;
        }
      `}</style>
    </div>
  )
}
