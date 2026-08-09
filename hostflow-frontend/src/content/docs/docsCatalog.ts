/** User docs catalog — Growth /docs hub (ADR-034 Phase 5). Locales: en, ru, pl. */

export type DocsLocale = 'en' | 'ru' | 'pl'
export type DocsText = Record<DocsLocale, string>

export type DocsStep = {
  title: DocsText
  body: DocsText
}

export type DocsArticle = {
  slug: string
  category: DocsText
  title: DocsText
  summary: DocsText
  seoTitle: DocsText
  seoDescription: DocsText
  minutes: number
  steps: DocsStep[]
  relatedFaq: string
  relatedSlugs: string[]
}

export const DOCS_ARTICLES: DocsArticle[] = [
  {
    slug: 'getting-started',
    category: { en: 'Start here', ru: 'Старт', pl: 'Start' },
    title: { en: 'Getting started with HostFlow', ru: 'С чего начать в HostFlow', pl: 'Jak zacząć w HostFlow' },
    summary: {
      en: 'Reach first hiring value in one sitting: company → vacancy → leads → contact.',
      ru: 'Дойдите до первой ценности за один заход: компания → вакансия → заявки → контакт.',
      pl: 'Do pierwszej wartości w jednym podejściu: firma → wakat → leady → kontakt.',
    },
    seoTitle: {
      en: 'Getting started | HostFlow Docs',
      ru: 'С чего начать | Документация HostFlow',
      pl: 'Jak zacząć | Dokumentacja HostFlow',
    },
    seoDescription: {
      en: 'Self-serve path from signup to first lead contact without waiting on support.',
      ru: 'Self-serve путь от регистрации до первого контакта с лидом без поддержки.',
      pl: 'Ścieżka self-serve od rejestracji do pierwszego kontaktu z leadem bez supportu.',
    },
    minutes: 5,
    steps: [
      {
        title: { en: 'Create your workspace', ru: 'Создайте workspace', pl: 'Utwórz workspace' },
        body: {
          en: 'Sign up at hostflow.cc, then complete the short company form (name, country, activity).',
          ru: 'Зарегистрируйтесь на hostflow.cc и заполните короткую форму компании (название, страна, деятельность).',
          pl: 'Zarejestruj się na hostflow.cc i wypełnij krótki formularz firmy (nazwa, kraj, działalność).',
        },
      },
      {
        title: { en: 'Follow the single next step', ru: 'Сделайте один следующий шаг', pl: 'Wykonaj jeden kolejny krok' },
        body: {
          en: 'On Setup / Launchpad, use the readiness checklist. Exactly one primary CTA is highlighted — do that first.',
          ru: 'На Setup / Launchpad смотрите readiness-чеклист. Подсвечен ровно один primary CTA — начните с него.',
          pl: 'Na Setup / Launchpad patrz na checklistę readiness. Podświetlony jest jeden primary CTA — zacznij od niego.',
        },
      },
      {
        title: { en: 'Create a vacancy, then open intake', ru: 'Создайте вакансию и откройте intake', pl: 'Utwórz wakat i otwórz intake' },
        body: {
          en: 'Empty vacancies point you to Create vacancy. Publish or open intake so applications have somewhere to land.',
          ru: 'Пустой список вакансий ведёт к «Создать вакансию». Опубликуйте / откройте intake, чтобы заявкам было куда падать.',
          pl: 'Pusta lista wakatów prowadzi do «Utwórz wakat». Opublikuj / otwórz intake, żeby zgłoszenia miały gdzie wylądować.',
        },
      },
      {
        title: { en: 'Connect Meta or skip with debt', ru: 'Подключите Meta или отложите', pl: 'Podłącz Meta albo odłóż' },
        body: {
          en: 'Meta is optional on day one. If you skip, the checklist keeps it visible as remaining work.',
          ru: 'Meta в первый день необязательна. Если отложите — пункт останется в чеклисте как долг.',
          pl: 'Meta pierwszego dnia jest opcjonalna. Jeśli odłożysz — pozycja zostanie na checkliście.',
        },
      },
      {
        title: { en: 'Contact the first lead', ru: 'Свяжитесь с первым лидом', pl: 'Skontaktuj się z pierwszym leadem' },
        body: {
          en: 'When a lead arrives, open Leads, claim ownership, and contact. Convert to candidate when qualified.',
          ru: 'Когда придёт лид — откройте Leads, возьмите ownership и свяжитесь. Квалифицированного конвертируйте в кандидата.',
          pl: 'Gdy przyjdzie lead — otwórz Leads, przejmij ownership i skontaktuj się. Po kwalifikacji konwertuj na kandydata.',
        },
      },
    ],
    relatedFaq: '/faq#launch_troubleshooting',
    relatedSlugs: ['create-company', 'first-vacancy', 'connect-meta'],
  },
  {
    slug: 'create-company',
    category: { en: 'Start here', ru: 'Старт', pl: 'Start' },
    title: { en: 'Create your company', ru: 'Создать компанию', pl: 'Utwórz firmę' },
    summary: {
      en: 'One short identity form — then the normal product shell with readiness UI.',
      ru: 'Одна короткая форма идентичности — дальше обычный продукт с readiness UI.',
      pl: 'Jeden krótki formularz tożsamości — potem zwykły produkt z readiness UI.',
    },
    seoTitle: {
      en: 'Create company | HostFlow Docs',
      ru: 'Создать компанию | Документация HostFlow',
      pl: 'Utwórz firmę | Dokumentacja HostFlow',
    },
    seoDescription: {
      en: 'How company setup works after signup — name, country, activity, no multi-step wizard trap.',
      ru: 'Как работает setup компании после регистрации — название, страна, деятельность, без wizard-ловушки.',
      pl: 'Jak działa setup firmy po rejestracji — nazwa, kraj, działalność, bez pułapki wizarda.',
    },
    minutes: 2,
    steps: [
      {
        title: { en: 'Open company setup', ru: 'Откройте setup компании', pl: 'Otwórz setup firmy' },
        body: {
          en: 'After signup HostFlow opens /app/platform/setup (or Setup hub) for company name, country, and activity.',
          ru: 'После регистрации HostFlow открывает /app/platform/setup (или Setup hub) для названия, страны и деятельности.',
          pl: 'Po rejestracji HostFlow otwiera /app/platform/setup (lub Setup hub) dla nazwy, kraju i działalności.',
        },
      },
      {
        title: { en: 'Save once', ru: 'Сохраните один раз', pl: 'Zapisz raz' },
        body: {
          en: 'You are not trapped in an 8-step wizard. After save you land in the CRM with a checklist and one next CTA.',
          ru: 'Вас не держат в 8-шаговом wizard. После сохранения — CRM с чеклистом и одним следующим CTA.',
          pl: 'Nie trzymamy Cię w 8-krokowym wizardzie. Po zapisie — CRM z checklistą i jednym kolejnym CTA.',
        },
      },
      {
        title: { en: 'Edit later in settings', ru: 'Правки позже в настройках', pl: 'Edycja później w ustawieniach' },
        body: {
          en: 'Company details can be updated from settings without re-running onboarding.',
          ru: 'Данные компании можно менять в настройках без повторного онбординга.',
          pl: 'Dane firmy możesz zmienić w ustawieniach bez ponownego onboardingu.',
        },
      },
    ],
    relatedFaq: '/faq#launch_troubleshooting',
    relatedSlugs: ['getting-started', 'invite-team'],
  },
  {
    slug: 'connect-meta',
    category: { en: 'Intake', ru: 'Сбор заявок', pl: 'Intake' },
    title: { en: 'Connect Meta ads', ru: 'Подключить Meta', pl: 'Podłącz Meta' },
    summary: {
      en: 'OAuth connect, map forms to vacancies, verify with a test lead.',
      ru: 'OAuth-подключение, привязка форм к вакансиям, проверка тестовым лидом.',
      pl: 'OAuth, mapowanie formularzy do wakatów, weryfikacja testowym leadem.',
    },
    seoTitle: {
      en: 'Connect Meta | HostFlow Docs',
      ru: 'Подключить Meta | Документация HostFlow',
      pl: 'Podłącz Meta | Dokumentacja HostFlow',
    },
    seoDescription: {
      en: 'Step-by-step Meta Business connect so lead forms land in the HostFlow pipeline.',
      ru: 'Пошаговое подключение Meta Business, чтобы формы лидов попадали в пайплайн HostFlow.',
      pl: 'Krok po kroku podłączenie Meta Business, aby formularze leadów trafiały do pipeline HostFlow.',
    },
    minutes: 8,
    steps: [
      {
        title: { en: 'Open Integrations → Meta', ru: 'Откройте Интеграции → Meta', pl: 'Otwórz Integracje → Meta' },
        body: {
          en: 'From readiness CTA or Settings → Integrations, start Connect. Use an admin of the Business that owns the ad account.',
          ru: 'Из readiness CTA или Настройки → Интеграции запустите Connect. Нужен админ Business с рекламным кабинетом.',
          pl: 'Z readiness CTA lub Ustawienia → Integracje uruchom Connect. Potrzebujesz admina Business z kontem reklam.',
        },
      },
      {
        title: { en: 'Approve HostFlow permissions', ru: 'Одобрите права HostFlow', pl: 'Zaakceptuj uprawnienia HostFlow' },
        body: {
          en: 'Grant ads/leads permissions. If Meta asks for App Review confirmation, a Business admin must accept.',
          ru: 'Выдайте права ads/leads. Если Meta просит App Review — подтверждает админ Business.',
          pl: 'Nadaj uprawnienia ads/leads. Jeśli Meta prosi o App Review — potwierdza admin Business.',
        },
      },
      {
        title: { en: 'Map forms to vacancies', ru: 'Привяжите формы к вакансиям', pl: 'Zmapuj formularze do wakatów' },
        body: {
          en: 'Map each lead form (or ad) to the vacancy / intake route so new leads open in the right context.',
          ru: 'Привяжите каждую форму (или объявление) к вакансии / intake — лиды попадут в нужный контекст.',
          pl: 'Zmapuj każdy formularz (lub reklamę) do wakatu / intake — leady trafią we właściwy kontekst.',
        },
      },
      {
        title: { en: 'Send a Meta test lead', ru: 'Отправьте тестовый лид Meta', pl: 'Wyślij testowy lead Meta' },
        body: {
          en: 'Use Meta’s test lead tool, then confirm the lead appears under Leads with correct vacancy ownership.',
          ru: 'Используйте test lead в Meta и убедитесь, что заявка появилась в Leads с нужной вакансией.',
          pl: 'Użyj test lead w Meta i sprawdź, że zgłoszenie jest w Leads z właściwym wakatem.',
        },
      },
    ],
    relatedFaq: '/faq#meta',
    relatedSlugs: ['first-lead', 'first-vacancy'],
  },
  {
    slug: 'first-vacancy',
    category: { en: 'Recruitment', ru: 'Рекрутинг', pl: 'Rekrutacja' },
    title: { en: 'Create your first vacancy', ru: 'Создать первую вакансию', pl: 'Utwórz pierwszy wakat' },
    summary: {
      en: 'A vacancy is the hiring container — pipeline, intake, and ownership hang off it.',
      ru: 'Вакансия — контейнер найма: пайплайн, intake и ownership завязаны на неё.',
      pl: 'Wakat to kontener rekrutacji: pipeline, intake i ownership są do niego przypięte.',
    },
    seoTitle: {
      en: 'First vacancy | HostFlow Docs',
      ru: 'Первая вакансия | Документация HostFlow',
      pl: 'Pierwszy wakat | Dokumentacja HostFlow',
    },
    seoDescription: {
      en: 'Create and publish a vacancy so Meta forms and applications have a place to land.',
      ru: 'Создайте и опубликуйте вакансию, чтобы формам Meta и заявкам было куда падать.',
      pl: 'Utwórz i opublikuj wakat, aby formularze Meta i zgłoszenia miały gdzie wylądować.',
    },
    minutes: 4,
    steps: [
      {
        title: { en: 'Open Vacancies', ru: 'Откройте Вакансии', pl: 'Otwórz Wakaty' },
        body: {
          en: 'From the empty state or readiness CTA, choose Create vacancy. Link it to the right company/client if needed.',
          ru: 'Из empty state или readiness CTA выберите «Создать вакансию». При необходимости привяжите компанию/клиента.',
          pl: 'Z empty state lub readiness CTA wybierz «Utwórz wakat». W razie potrzeby powiąż firmę/klienta.',
        },
      },
      {
        title: { en: 'Fill role essentials', ru: 'Заполните суть роли', pl: 'Uzupełnij esencję roli' },
        body: {
          en: 'Title, location/region, and hiring context are enough to start. You can refine requirements later.',
          ru: 'Достаточно названия, локации/региона и контекста найма. Требования можно уточнить позже.',
          pl: 'Wystarczy tytuł, lokalizacja/region i kontekst rekrutacji. Wymagania doprecyzujesz później.',
        },
      },
      {
        title: { en: 'Open intake / publish', ru: 'Откройте intake / опубликуйте', pl: 'Otwórz intake / opublikuj' },
        body: {
          en: 'Make the vacancy ready to receive applications, then map Meta forms or share the public intake link.',
          ru: 'Сделайте вакансию готовой принимать заявки, затем привяжите формы Meta или поделитесь public intake.',
          pl: 'Przygotuj wakat na zgłoszenia, potem zmapuj formularze Meta lub udostępnij public intake.',
        },
      },
    ],
    relatedFaq: '/faq#recruitment',
    relatedSlugs: ['getting-started', 'first-lead', 'connect-meta'],
  },
  {
    slug: 'first-lead',
    category: { en: 'Recruitment', ru: 'Рекрутинг', pl: 'Rekrutacja' },
    title: { en: 'Receive and work your first lead', ru: 'Принять и обработать первый лид', pl: 'Przyjąć i obsłużyć pierwszy lead' },
    summary: {
      en: 'Leads land owned in one pipeline — contact fast, then qualify.',
      ru: 'Лиды попадают в один owned-пайплайн — быстро свяжитесь и квалифицируйте.',
      pl: 'Leady lądują w jednym owned pipeline — szybko skontaktuj się i kwalifikuj.',
    },
    seoTitle: {
      en: 'First lead | HostFlow Docs',
      ru: 'Первый лид | Документация HostFlow',
      pl: 'Pierwszy lead | Dokumentacja HostFlow',
    },
    seoDescription: {
      en: 'How inbound applications appear in Leads and what to do first.',
      ru: 'Как входящие заявки появляются в Leads и что делать первым.',
      pl: 'Jak zgłoszenia pojawiają się w Leads i co zrobić najpierw.',
    },
    minutes: 5,
    steps: [
      {
        title: { en: 'Confirm intake path', ru: 'Проверьте путь intake', pl: 'Sprawdź ścieżkę intake' },
        body: {
          en: 'Vacancy exists and Meta form (or public apply link) is mapped. Without that, Leads stays empty for a reason.',
          ru: 'Вакансия есть, форма Meta (или public apply) привязана. Иначе Leads пустой по понятной причине.',
          pl: 'Wakat istnieje, formularz Meta (lub public apply) jest zmapowany. Inaczej Leads jest pusty z jasnego powodu.',
        },
      },
      {
        title: { en: 'Open Leads', ru: 'Откройте Leads', pl: 'Otwórz Leads' },
        body: {
          en: 'New applications appear with vacancy context. Take ownership so teammates know who follows up.',
          ru: 'Новые заявки появляются с контекстом вакансии. Возьмите ownership, чтобы команда знала, кто ведёт.',
          pl: 'Nowe zgłoszenia mają kontekst wakatu. Przejmij ownership, by zespół wiedział, kto prowadzi.',
        },
      },
      {
        title: { en: 'Contact and set next action', ru: 'Свяжитесь и задайте next action', pl: 'Skontaktuj się i ustaw next action' },
        body: {
          en: 'Call/message, log the outcome, and keep one clear next step. Qualify → convert to candidate when ready.',
          ru: 'Позвоните/напишите, зафиксируйте итог и один next step. При квалификации — convert в кандидата.',
          pl: 'Zadzwoń/napisz, zapisz wynik i jeden next step. Po kwalifikacji — convert na kandydata.',
        },
      },
    ],
    relatedFaq: '/faq#recruitment',
    relatedSlugs: ['first-candidate', 'connect-meta', 'first-vacancy'],
  },
  {
    slug: 'first-candidate',
    category: { en: 'Recruitment', ru: 'Рекрутинг', pl: 'Rekrutacja' },
    title: { en: 'Convert a lead to a candidate', ru: 'Конвертировать лид в кандидата', pl: 'Konwertuj lead na kandydata' },
    summary: {
      en: 'Candidates are the hiring track after qualification — stages, documents, ownership.',
      ru: 'Кандидат — трек найма после квалификации: этапы, документы, ownership.',
      pl: 'Kandydat to tor rekrutacji po kwalifikacji: etapy, dokumenty, ownership.',
    },
    seoTitle: {
      en: 'First candidate | HostFlow Docs',
      ru: 'Первый кандидат | Документация HostFlow',
      pl: 'Pierwszy kandydat | Dokumentacja HostFlow',
    },
    seoDescription: {
      en: 'Qualify a lead and move them into the candidate pipeline with clear ownership.',
      ru: 'Квалифицируйте лид и переведите в пайплайн кандидатов с ясным владельцем.',
      pl: 'Zakwalifikuj lead i przenieś do pipeline kandydatów z jasnym ownership.',
    },
    minutes: 4,
    steps: [
      {
        title: { en: 'Qualify in Leads', ru: 'Квалифицируйте в Leads', pl: 'Zakwalifikuj w Leads' },
        body: {
          en: 'When the person fits the vacancy, use Convert / promote to candidate (wording may vary by screen).',
          ru: 'Если человек подходит под вакансию — Convert / promote в кандидата (формулировка зависит от экрана).',
          pl: 'Jeśli osoba pasuje do wakatu — Convert / promote na kandydata (brzmienie zależy od ekranu).',
        },
      },
      {
        title: { en: 'Move pipeline stages', ru: 'Двигайте этапы пайплайна', pl: 'Przesuwaj etapy pipeline' },
        body: {
          en: 'Advance stages as you interview and collect documents. Keep the next action visible.',
          ru: 'Продвигайте этапы по мере интервью и сбора документов. Держите next action видимым.',
          pl: 'Przesuwaj etapy wraz z rozmowami i dokumentami. Trzymaj next action widoczne.',
        },
      },
      {
        title: { en: 'Request documents when needed', ru: 'Запросите документы при необходимости', pl: 'Poproś o dokumenty, gdy trzeba' },
        body: {
          en: 'Use document slots / public upload links so compliance does not live in chat screenshots.',
          ru: 'Используйте слоты документов / public upload — compliance не должен жить в скринах чатов.',
          pl: 'Używaj slotów dokumentów / public upload — compliance nie powinien żyć na zrzutach czatu.',
        },
      },
    ],
    relatedFaq: '/faq#recruitment',
    relatedSlugs: ['first-lead', 'documents-basics'],
  },
  {
    slug: 'documents-basics',
    category: { en: 'Documents', ru: 'Документы', pl: 'Dokumenty' },
    title: { en: 'Document control basics', ru: 'Основы контроля документов', pl: 'Podstawy kontroli dokumentów' },
    summary: {
      en: 'Required slots, uploads, and status — one place instead of messenger folders.',
      ru: 'Нужные слоты, загрузки и статусы — одно место вместо папок в мессенджерах.',
      pl: 'Wymagane sloty, uploady i statusy — jedno miejsce zamiast folderów w messengerach.',
    },
    seoTitle: {
      en: 'Documents basics | HostFlow Docs',
      ru: 'Документы: основы | Документация HostFlow',
      pl: 'Dokumenty: podstawy | Dokumentacja HostFlow',
    },
    seoDescription: {
      en: 'How HostFlow tracks required candidate documents and public upload links.',
      ru: 'Как HostFlow ведёт обязательные документы кандидата и public upload.',
      pl: 'Jak HostFlow śledzi wymagane dokumenty kandydata i public upload.',
    },
    minutes: 5,
    steps: [
      {
        title: { en: 'Open candidate documents', ru: 'Откройте документы кандидата', pl: 'Otwórz dokumenty kandydata' },
        body: {
          en: 'From the candidate card, open Documents to see required vs received slots.',
          ru: 'В карточке кандидата откройте Documents — видны required vs полученные слоты.',
          pl: 'W karcie kandydata otwórz Documents — widać required vs otrzymane sloty.',
        },
      },
      {
        title: { en: 'Share upload link if needed', ru: 'При необходимости дайте upload-ссылку', pl: 'W razie potrzeby daj link upload' },
        body: {
          en: 'Send the public documents link so the candidate uploads without emailing files to recruiters.',
          ru: 'Отправьте public documents link — кандидат загружает сам, без пересылки файлов рекрутерам.',
          pl: 'Wyślij public documents link — kandydat wgrywa sam, bez mailowania plików rekruterom.',
        },
      },
      {
        title: { en: 'Track status to hire', ru: 'Ведите статус до найма', pl: 'Śledź status do hire' },
        body: {
          en: 'Missing/expired docs stay visible on the card so placement is not blocked by surprise paperwork.',
          ru: 'Недостающие/просроченные документы видны на карточке — placement не блокируется сюрпризом.',
          pl: 'Braki/wygasłe dokumenty widać na karcie — placement nie pada na niespodziance papierkowej.',
        },
      },
    ],
    relatedFaq: '/faq#documents',
    relatedSlugs: ['first-candidate'],
  },
  {
    slug: 'invite-team',
    category: { en: 'Team', ru: 'Команда', pl: 'Zespół' },
    title: { en: 'Invite teammates', ru: 'Пригласить коллег', pl: 'Zaproś zespół' },
    summary: {
      en: 'Optional on day one — hire solo first, then share ownership of vacancies and leads.',
      ru: 'В первый день необязательно — можно начать одному, затем делить ownership вакансий и лидов.',
      pl: 'Pierwszego dnia opcjonalne — możesz zacząć solo, potem dzielić ownership wakatów i leadów.',
    },
    seoTitle: {
      en: 'Invite team | HostFlow Docs',
      ru: 'Пригласить команду | Документация HostFlow',
      pl: 'Zaproś zespół | Dokumentacja HostFlow',
    },
    seoDescription: {
      en: 'Invite recruiters so leads and candidates stay owned in one workspace.',
      ru: 'Пригласите рекрутеров, чтобы лиды и кандидаты велись в одном workspace.',
      pl: 'Zaproś rekruterów, by leady i kandydaci były prowadzone w jednym workspace.',
    },
    minutes: 3,
    steps: [
      {
        title: { en: 'Open Users / Team settings', ru: 'Откройте Пользователи / Команда', pl: 'Otwórz Użytkownicy / Zespół' },
        body: {
          en: 'From readiness checklist or Settings, send an invite email with the right role.',
          ru: 'Из readiness-чеклиста или Настроек отправьте invite с нужной ролью.',
          pl: 'Z checklisty readiness lub Ustawień wyślij invite z właściwą rolą.',
        },
      },
      {
        title: { en: 'Assign vacancy ownership', ru: 'Назначьте ownership вакансий', pl: 'Przypisz ownership wakatów' },
        body: {
          en: 'After they join, share vacancies/leads so work is not trapped in private spreadsheets.',
          ru: 'После входа раздайте вакансии/лиды — работа не должна жить в личных Excel.',
          pl: 'Po dołączeniu przydziel wakaty/leady — praca nie może żyć w prywatnych arkuszach.',
        },
      },
    ],
    relatedFaq: '/faq#getting_started',
    relatedSlugs: ['getting-started', 'create-company'],
  },
]

export function docsLocaleFromApp(locale: string | undefined): DocsLocale {
  if (!locale) return 'en'
  if (locale.startsWith('ru')) return 'ru'
  if (locale.startsWith('pl')) return 'pl'
  return 'en'
}

export function getDocsArticle(slug: string): DocsArticle | undefined {
  return DOCS_ARTICLES.find((article) => article.slug === slug)
}

export function docsCategories(locale: DocsLocale): { id: string; title: string; articles: DocsArticle[] }[] {
  const order: string[] = []
  const map = new Map<string, DocsArticle[]>()
  for (const article of DOCS_ARTICLES) {
    const key = article.category.en
    if (!map.has(key)) {
      map.set(key, [])
      order.push(key)
    }
    map.get(key)!.push(article)
  }
  return order.map((key) => {
    const articles = map.get(key)!
    return {
      id: key.toLowerCase().replace(/\s+/g, '_'),
      title: articles[0].category[locale],
      articles,
    }
  })
}
