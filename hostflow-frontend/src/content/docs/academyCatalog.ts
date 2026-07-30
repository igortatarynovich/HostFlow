/** Academy lessons — Growth /academy (ADR-034 Phase 5). Links to /docs; video optional. */

import type { DocsLocale } from './docsCatalog'

export type AcademyLesson = {
  id: string
  title: Record<DocsLocale, string>
  summary: Record<DocsLocale, string>
  minutes: number
  docsSlug: string
  /** Optional YouTube (or other) embed URL — omit until real assets exist. */
  videoUrl?: string
}

export const ACADEMY_LESSONS: AcademyLesson[] = [
  {
    id: 'start',
    title: { en: 'Getting started path', ru: 'Путь старта', pl: 'Ścieżka startu' },
    summary: {
      en: 'Company → next CTA → vacancy → lead → contact in one sitting.',
      ru: 'Компания → next CTA → вакансия → лид → контакт за один заход.',
      pl: 'Firma → next CTA → wakat → lead → kontakt w jednym podejściu.',
    },
    minutes: 5,
    docsSlug: 'getting-started',
  },
  {
    id: 'company',
    title: { en: 'Company identity (2 min)', ru: 'Идентичность компании (2 мин)', pl: 'Tożsamość firmy (2 min)' },
    summary: {
      en: 'Short form once — then readiness UI, not a wizard trap.',
      ru: 'Короткая форма один раз — дальше readiness UI, не wizard.',
      pl: 'Krótki formularz raz — potem readiness UI, nie wizard.',
    },
    minutes: 2,
    docsSlug: 'create-company',
  },
  {
    id: 'meta',
    title: { en: 'Meta ads intake', ru: 'Сбор лидов из Meta', pl: 'Intake z Meta' },
    summary: {
      en: 'Connect, map forms, send a test lead.',
      ru: 'Подключить, привязать формы, отправить тестовый лид.',
      pl: 'Podłącz, zmapuj formularze, wyślij testowy lead.',
    },
    minutes: 8,
    docsSlug: 'connect-meta',
  },
  {
    id: 'vacancy',
    title: { en: 'First vacancy', ru: 'Первая вакансия', pl: 'Pierwszy wakat' },
    summary: {
      en: 'Create the hiring container and open intake.',
      ru: 'Создайте контейнер найма и откройте intake.',
      pl: 'Utwórz kontener rekrutacji i otwórz intake.',
    },
    minutes: 4,
    docsSlug: 'first-vacancy',
  },
  {
    id: 'lead',
    title: { en: 'First lead', ru: 'Первый лид', pl: 'Pierwszy lead' },
    summary: {
      en: 'Own the application, contact, set next action.',
      ru: 'Возьмите заявку, свяжитесь, задайте next action.',
      pl: 'Przejmij zgłoszenie, skontaktuj się, ustaw next action.',
    },
    minutes: 5,
    docsSlug: 'first-lead',
  },
  {
    id: 'candidate',
    title: { en: 'First candidate', ru: 'Первый кандидат', pl: 'Pierwszy kandydat' },
    summary: {
      en: 'Qualify → convert → move stages and documents.',
      ru: 'Квалификация → convert → этапы и документы.',
      pl: 'Kwalifikacja → convert → etapy i dokumenty.',
    },
    minutes: 4,
    docsSlug: 'first-candidate',
  },
  {
    id: 'documents',
    title: { en: 'Documents in hiring', ru: 'Документы в найме', pl: 'Dokumenty w rekrutacji' },
    summary: {
      en: 'Slots, public upload, status until hire.',
      ru: 'Слоты, public upload, статус до hire.',
      pl: 'Sloty, public upload, status do hire.',
    },
    minutes: 5,
    docsSlug: 'documents-basics',
  },
  {
    id: 'team',
    title: { en: 'Invite the team', ru: 'Пригласить команду', pl: 'Zaproś zespół' },
    summary: {
      en: 'Optional day-one — share ownership when you scale.',
      ru: 'В первый день необязательно — делитесь ownership при масштабе.',
      pl: 'Pierwszego dnia opcjonalne — dziel ownership przy skali.',
    },
    minutes: 3,
    docsSlug: 'invite-team',
  },
]

export function academyLocaleFromApp(locale: string | undefined): DocsLocale {
  if (!locale) return 'en'
  if (locale.startsWith('ru')) return 'ru'
  if (locale.startsWith('pl')) return 'pl'
  return 'en'
}
