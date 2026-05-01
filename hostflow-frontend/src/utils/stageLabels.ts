// Shared helpers to normalize and translate stage/reason labels that may arrive
// in different languages or formats from the API.

export type TranslateFn = (key: string, opts?: { defaultValue?: string; values?: Record<string, any> }) => string

const normalizeKey = (value?: string | null) => {
  if (!value) return ''
  const normalized = String(value)
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
  return normalized
    .replace(/[^a-z0-9\u0400-\u04ff]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

const STAGE_CODE_ALIASES: Record<string, string> = {
  hired: 'employed',
  employeed: 'employed',
  employment: 'employed',
  probation: 'probation_ok',
  probation_done: 'probation_ok',
  probation_ok: 'probation_ok',
  hired_stage: 'employed',
}

const STAGE_LABEL_ALIASES: Record<string, string> = {
  new: 'new',
  new_lead: 'new',
  новый: 'new',
  nowy: 'new',
  nowy_: 'new',
  nowy_lead: 'new',
  contacted: 'contacted',
  contact_established: 'contacted',
  контакт_установлен: 'contacted',
  kontakt_nawiązany: 'contacted',
  kontakt_nawiazany: 'contacted',
  kontakt_nawiązany_: 'contacted',
  interview: 'contacted',
  questionnaire_submitted: 'questionnaire_submitted',
  анкета_заполнена: 'questionnaire_submitted',
  kwestionariusz_wysłany: 'questionnaire_submitted',
  kwestionariusz_wyslany: 'questionnaire_submitted',
  waiting_for_documents: 'docs_wait',
  awaiting_documents: 'docs_wait',
  ожидаем_документы: 'docs_wait',
  czekamy_na_dokumenty: 'docs_wait',
  czekamy_na_dokumenty_: 'docs_wait',
  documents_received: 'docs_got',
  документы_получены: 'docs_got',
  dokumenty_otrzymane: 'docs_got',
  dokumenty_otrzymane_: 'docs_got',
  work_permit_ordered: 'permit_ordered',
  заказ_разрешения: 'permit_ordered',
  zamowiono_zezwolenie: 'permit_ordered',
  work_permit_received: 'permit_received',
  разрешение_получено: 'permit_received',
  zezwolenie_odebrane: 'permit_received',
  visa_in_progress: 'visa',
  виза: 'visa',
  red_paper_ordered: 'red_paper',
  красная_бумага_заказана: 'red_paper',
  trip_planned: 'trip_plan',
  plan_trip: 'trip_plan',
  планируем_приезд: 'trip_plan',
  planowany_przyjazd: 'trip_plan',
  at_client_base: 'at_client',
  на_базе_клиента: 'at_client',
  na_bazie_klienta: 'at_client',
  employment_pending: 'employment_pending',
  на_трудоустройстве: 'employment_pending',
  w_trakcie_zatrudnienia: 'employment_pending',
  employed: 'employed',
  hired: 'employed',
  трудоустроен: 'employed',
  zatrudniony: 'employed',
  on_trip: 'on_trip',
  в_рейсе: 'on_trip',
  probation_passed: 'probation_ok',
  probation_completed: 'probation_ok',
  probation_ok: 'probation_ok',
  прошёл_пробный_период: 'probation_ok',
  okres_próbny_zakończony: 'probation_ok',
  rejected: 'rejected',
  отклонён: 'rejected',
  odrzucony: 'rejected',
  odrzucony_: 'rejected',
  declined: 'declined',
  candidate_declined: 'declined',
  отказался: 'declined',
  kandydat_zrezygnował: 'declined',
  kandydat_zrezygnowal: 'declined',
  no_answer: 'no_answer',
  не_отвечает: 'no_answer',
  brak_kontaktu: 'no_answer',
  brak_kontaktu_: 'no_answer',
  ready_for_handoff: 'ready_for_handoff',
  gotowy_do_przekazania: 'ready_for_handoff',
  processing_by_client: 'processing_by_client',
  procesowany_przez_zleceniodawce: 'processing_by_client',
  docs_submitted_permit: 'docs_submitted_permit',
  zlozono_dokumenty_na_zezwolenie: 'docs_submitted_permit',
  handoff_returned: 'handoff_returned',
  zwrocono: 'handoff_returned',
}

const REASON_LABEL_ALIASES: Record<string, string> = {
  schedule_mismatch: 'schedule',
  schedule: 'schedule',
  недоступен_график: 'schedule',
  bez_dopasowania_grafiku: 'schedule',
  salary_expectations: 'salary',
  salary_expectations_: 'salary',
  salary_expectation: 'salary',
  'salary expectations': 'salary',
  salary: 'salary',
  зарплата: 'salary',
  не_устраивает_зарплата: 'salary',
  oczekiwania_płacowe: 'salary',
  oczekiwania_placowe: 'salary',
  base_location_not_suitable: 'location',
  location_mismatch: 'location',
  расположение_не_подходит: 'location',
  lokalizacja_nie_odpowiada: 'location',
  trailer_type_mismatch: 'trailer_type',
  trailer_type: 'trailer_type',
  не_устраивает_тип_полуприцепа: 'trailer_type',
  typ_naczepy: 'trailer_type',
  no_night_driving: 'night_driving',
  night_driving: 'night_driving',
  bonus_scheme_mismatch: 'bonus_scheme',
  bonus_scheme: 'bonus_scheme',
  cab_sleep: 'cab_overnight',
  does_not_want_to_sleep_in_cab: 'cab_overnight',
  не_хочет_спать_в_кабине: 'cab_overnight',
  nie_chce_spać_w_kabinie: 'cab_overnight',
  negative_company_reviews: 'company_reviews',
  poor_company_reviews: 'company_reviews',
  негативные_отзывы: 'company_reviews',
  słabe_opinie: 'company_reviews',
  eu_experience_less_than_1_year: 'eu_exp_lt_1y',
  eu_exp_lt_one_year: 'eu_exp_lt_1y',
  опыт_по_ес_менее_1_года: 'eu_exp_lt_1y',
  eu_experience_less_than_6_months: 'eu_exp_lt_6m',
  опыт_по_ес_менее_6_месяцев: 'eu_exp_lt_6m',
  awaiting_residence_permit: 'awaiting_residence',
  waiting_for_residence: 'awaiting_residence',
  ожидает_внж: 'awaiting_residence',
  czeka_na_kartę_pobytu: 'awaiting_residence',
  czeka_na_karte_pobytu: 'awaiting_residence',
  language_barrier: 'language',
  missing_language: 'language',
  нет_языка: 'language',
  no_visa_or_residence_permit: 'no_visa',
  no_visa_residence_permit: 'no_visa',
  'no visa / residence permit': 'no_visa',
  no_residence_permit: 'no_visa',
  no_visa: 'no_visa',
  нет_визы_внж: 'no_visa',
  нет_визы: 'no_visa',
  no_ce_experience: 'no_ce_experience',
  lacks_ce_experience: 'no_ce_experience',
  нет_опыта_ce: 'no_ce_experience',
  нет_опыта_по_ce: 'no_ce_experience',
  no_code_95: 'no_code95',
  no_code_95_: 'no_code95',
  'no code 95': 'no_code95',
  missing_code_95: 'no_code95',
  нет_95_кода: 'no_code95',
  no_tachograph_card: 'no_chip',
  missing_tachograph_card: 'no_chip',
  нет_карты_тахографа: 'no_chip',
  нет_чипа: 'no_chip',
  age_restrictions: 'age',
  age: 'age',
  возраст: 'age',
  blacklisted: 'blacklist',
  чёрный_список: 'blacklist',
  wrong_phone: 'wrong_phone',
  incorrect_phone_number: 'wrong_phone',
  wrong_phone_number: 'wrong_phone',
  wrong_number: 'wrong_phone',
  invalid_phone: 'wrong_phone',
  неверно_указан_номер: 'wrong_phone',
  неверный_номер: 'wrong_phone',
  неверный_номер_телефона: 'wrong_phone',
  nieprawidlowy_numer: 'wrong_phone',
  nieprawidlowy_numer_telefonu: 'wrong_phone',
  bez_przyczyny: 'no_reason',
  без_причины: 'no_reason',
}

const STAGE_FALLBACK_LABELS: Record<string, string> = {
  new: 'Новый',
  no_answer: 'Не отвечает',
  contacted: 'Контакт установлен',
  questionnaire_submitted: 'Анкета заполнена',
  docs_wait: 'Ожидаем документы',
  docs_got: 'Документы получены',
  permit_ordered: 'Заказ разрешения на работу',
  permit_received: 'Разрешение на работу получено',
  visa: 'Виза',
  red_paper: 'Красная бумага заказана',
  red_paper_ordered: 'Красная бумага заказана',
  trip_plan: 'Планируем приезд',
  at_client: 'На базе клиента',
  on_trip: 'Выехал в рейс',
  interview: 'Контакт установлен',
  hiring: 'Документы получены',
  employed: 'Трудоустроен',
  probation: 'Испытательный срок',
  probation_ok: 'Испытательный срок',
  rejected: 'Отказ',
  declined: 'Отказался',
  ready_for_handoff: 'Готов к передаче',
  processing_by_client: 'Обработка заказчиком',
  docs_submitted_permit: 'Документы поданы на разрешение',
  handoff_returned: 'Возвращён',
  open: 'Открыта',
  paused: 'Пауза',
  closed: 'Закрыта',
}

const buildNormalizedMap = (source: Record<string, string>) =>
  Object.fromEntries(
    Object.entries(source)
      .map(([key, value]) => [normalizeKey(key), value])
      .filter(([key]) => Boolean(key)),
  )

const NORMALIZED_STAGE_CODE_ALIASES = buildNormalizedMap(STAGE_CODE_ALIASES)
const NORMALIZED_STAGE_LABEL_ALIASES = buildNormalizedMap(STAGE_LABEL_ALIASES)
const NORMALIZED_REASON_LABEL_ALIASES = buildNormalizedMap(REASON_LABEL_ALIASES)

export const normalizeLabelKey = normalizeKey

export const canonicalStageKey = (code?: string | null, fallback?: string | null): string | null => {
  const normalized = normalizeKey(code)
  if (normalized) {
    return (
      NORMALIZED_STAGE_CODE_ALIASES[normalized] ??
      NORMALIZED_STAGE_LABEL_ALIASES[normalized] ??
      normalized
    )
  }
  const fallbackKey = normalizeKey(fallback)
  if (fallbackKey) {
    return NORMALIZED_STAGE_LABEL_ALIASES[fallbackKey] ?? fallbackKey
  }
  return null
}

export const canonicalReasonKey = (code?: string | null, fallback?: string | null): string | null => {
  const normalized = normalizeKey(code)
  if (normalized) {
    return NORMALIZED_REASON_LABEL_ALIASES[normalized] ?? normalized
  }
  const fallbackKey = normalizeKey(fallback)
  if (fallbackKey) {
    return NORMALIZED_REASON_LABEL_ALIASES[fallbackKey] ?? fallbackKey
  }
  return null
}

export function translateStageLabel(
  t: TranslateFn,
  code?: string | null,
  fallback?: string | null,
): string {
  const canonical = canonicalStageKey(code, fallback)
  const normalized = normalizeKey(code) || normalizeKey(fallback)
  const lookupKey = canonical ?? normalized
  if (lookupKey) {
    const translated =
      t(`app.dashboard.stage_labels.${lookupKey}`, { defaultValue: '' }) ||
      t(`app.candidates.stage_labels.${lookupKey}`, { defaultValue: '' })
    if (translated) {
      return translated
    }
    if (STAGE_FALLBACK_LABELS[lookupKey]) {
      return STAGE_FALLBACK_LABELS[lookupKey]
    }
  }
  if (fallback && String(fallback).trim()) return String(fallback)
  if (code && String(code).trim()) return String(code)
  return '—'
}

export function translateReasonLabel(
  t: TranslateFn,
  code?: string | null,
  fallback?: string | null,
): string {
  const canonical = canonicalReasonKey(code, fallback)
  const normalized = normalizeKey(code) || normalizeKey(fallback)
  const lookupKey = canonical ?? normalized
  if (lookupKey) {
    if (lookupKey === 'no_reason') {
      return t('app.dashboard.labels.no_reason', { defaultValue: '' }) || ''
    }
    const translated = t(`app.dashboard.reason_codes.${lookupKey}`, { defaultValue: '' })
    if (translated) {
      return translated
    }
  }
  if (fallback && String(fallback).trim()) return String(fallback)
  if (code && String(code).trim()) return String(code)
  return ''
}
