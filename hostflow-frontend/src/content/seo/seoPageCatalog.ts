/** SEO marketing page catalog — Wave-2 factory (ADR-034 Growth). */

export type SeoLocale = 'en' | 'ru' | 'pl'
export type SeoText = Record<SeoLocale, string>
export type SeoPageType = 'feature' | 'use_case' | 'comparison'

export type SeoFaqItem = { q: SeoText; a: SeoText }
export type SeoRelatedLink = { path: string; label: SeoText }

export type SeoPageDefinition = {
  id: string
  path: string
  pageType: SeoPageType
  badge: SeoText
  seoTitle: SeoText
  seoDescription: SeoText
  h1: SeoText
  subtitle: SeoText
  problemTitle: SeoText
  problemItems: SeoText[]
  solutionTitle: SeoText
  solutionBody: SeoText
  flowTitle: SeoText
  flowItems: SeoText[]
  faq: SeoFaqItem[]
  related: SeoRelatedLink[]
}

export const SEO_PAGE_CATALOG: SeoPageDefinition[] = [
  {
    id: "recruitment_agencies",
    path: "/use-cases/recruitment-agencies",
    pageType: "use_case",
    badge: { en: "Use-case", ru: "Сценарий", pl: "Use-case" },
    seoTitle: { en: "CRM for Recruitment Agencies | HostFlow", ru: "CRM для кадровых агентств | HostFlow", pl: "CRM dla agencji rekrutacyjnych | HostFlow" },
    seoDescription: { en: "Run agency hiring from Meta leads to placement: owned pipeline, recruiter load, and documents in one HostFlow workspace.", ru: "Ведите найм агентства от лидов Meta до размещения: пайплайн, нагрузка рекрутеров и документы в одном HostFlow.", pl: "Prowadź rekrutację agencji od leadów Meta do placement: pipeline, obciążenie rekruterów i dokumenty w jednym HostFlow." },
    h1: { en: "CRM for Recruitment Agencies", ru: "CRM для кадровых агентств", pl: "CRM dla agencji rekrutacyjnych" },
    subtitle: { en: "Close client vacancies faster — capture leads, assign recruiters, and keep every candidate owned until placement.", ru: "Закрывайте вакансии клиентов быстрее — собирайте лиды, назначайте рекрутеров и ведите кандидатов до размещения.", pl: "Zamykaj wakaty klientów szybciej — zbieraj leady, przypisuj rekruterów i prowadź kandydatów do placement." },
    problemTitle: { en: "What breaks in agency hiring", ru: "Где ломается найм в агентстве", pl: "Gdzie psuje się rekrutacja w agencji" },
    problemItems: [
      { en: "Leads from ads land in chats with no owner.", ru: "Лиды из рекламы падают в чаты без владельца.", pl: "Leady z reklam lądują na czatach bez właściciela." },
      { en: "Each recruiter keeps a private spreadsheet.", ru: "У каждого рекрутера свой Excel.", pl: "Każdy rekruter ma własny arkusz." },
      { en: "Clients ask for status you cannot prove.", ru: "Клиент спрашивает статус, который нельзя доказать.", pl: "Klient pyta o status, którego nie da się udowodnić." },
    ],
    solutionTitle: { en: "How HostFlow helps agencies", ru: "Как HostFlow помогает агентствам", pl: "Jak HostFlow pomaga agencjom" },
    solutionBody: { en: "One shared pipeline per vacancy, automatic intake from Meta and forms, and clear ownership so placements stop slipping.", ru: "Общий пайплайн по вакансии, авто-сбор из Meta и форм и ясная ответственность — размещения не «теряются».", pl: "Wspólny pipeline na wakat, automatyczny intake z Meta i formularzy oraz jasny ownership — placementy się nie gubią." },
    flowTitle: { en: "Agency flow in HostFlow", ru: "Поток агентства в HostFlow", pl: "Przepływ agencji w HostFlow" },
    flowItems: [
      { en: "Connect Meta and map forms to client vacancies.", ru: "Подключите Meta и привяжите формы к вакансиям клиентов.", pl: "Podłącz Meta i zmapuj formularze do wakatów klientów." },
      { en: "Distribute leads to recruiters with next actions.", ru: "Распределите лиды рекрутерам со следующими шагами.", pl: "Rozdziel leady rekruterom z kolejnymi krokami." },
      { en: "Track documents and stages until placement.", ru: "Ведите документы и этапы до размещения.", pl: "Śledź dokumenty i etapy aż do placement." },
      { en: "Report progress from one source of truth.", ru: "Отчитывайтесь из одного источника правды.", pl: "Raportuj postęp z jednego źródła prawdy." },
    ],
    faq: [
      {
        q: { en: "Can multiple recruiters share one vacancy?", ru: "Могут ли несколько рекрутеров вести одну вакансию?", pl: "Czy kilku rekruterów może prowadzić jeden wakat?" },
        a: { en: "Yes. Ownership and stages stay visible to the team.", ru: "Да. Владелец и этапы видны всей команде.", pl: "Tak. Ownership i etapy są widoczne dla zespołu." },
      },
      {
        q: { en: "Does it work for multi-client agencies?", ru: "Подходит ли для агентств с несколькими клиентами?", pl: "Czy pasuje do agencji z wieloma klientami?" },
        a: { en: "Yes. Companies and vacancies keep client context separated.", ru: "Да. Компании и вакансии держат контекст клиентов раздельно.", pl: "Tak. Firmy i wakaty trzymają kontekst klientów osobno." },
      },
      {
        q: { en: "How fast can we start?", ru: "Как быстро можно стартовать?", pl: "Jak szybko możemy zacząć?" },
        a: { en: "Self-serve: company → vacancy → Meta → first lead without a sales call.", ru: "Self-serve: компания → вакансия → Meta → первый лид без звонка в sales.", pl: "Self-serve: firma → wakat → Meta → pierwszy lead bez rozmowy ze sales." },
      },
    ],
    related: [
      { path: "/features/candidate-pipeline", label: { en: "Candidate pipeline", ru: "Пайплайн кандидатов", pl: "Pipeline kandydatów" } },
      { path: "/features/meta-ads-recruitment", label: { en: "Meta ads intake", ru: "Лиды из Meta", pl: "Intake z Meta" } },
      { path: "/use-cases/trucking-recruitment", label: { en: "Trucking recruitment", ru: "Рекрутинг водителей", pl: "Rekrutacja kierowców" } },
      { path: "/faq", label: { en: "FAQ", ru: "FAQ", pl: "FAQ" } },
    ],
  },
  {
    id: "transport_companies",
    path: "/use-cases/transport-companies",
    pageType: "use_case",
    badge: { en: "Use-case", ru: "Сценарий", pl: "Use-case" },
    seoTitle: { en: "CRM for Transport Companies | HostFlow", ru: "CRM для транспортных компаний | HostFlow", pl: "CRM dla firm transportowych | HostFlow" },
    seoDescription: { en: "Hire drivers and warehouse staff faster with HostFlow: Meta intake, pipeline ownership, and document readiness before dispatch.", ru: "Нанимайте водителей и склад быстрее с HostFlow: Meta, пайплайн и готовность документов до выхода в рейс.", pl: "Zatrudniaj kierowców i magazyn szybciej z HostFlow: Meta, pipeline i gotowość dokumentów przed wyjazdem." },
    h1: { en: "CRM for Transport Companies", ru: "CRM для транспортных компаний", pl: "CRM dla firm transportowych" },
    subtitle: { en: "Keep hiring operational — from ad lead to documents ready for the first trip.", ru: "Держите найм операционным — от лида из рекламы до документов к первому рейсу.", pl: "Utrzymaj rekrutację operacyjną — od leada z reklamy do dokumentów na pierwszy wyjazd." },
    problemTitle: { en: "Transport hiring pain", ru: "Боль транспортного найма", pl: "Ból rekrutacji w transporcie" },
    problemItems: [
      { en: "CE/driver paperwork blocks dispatch.", ru: "Документы CE/водителей блокируют выход.", pl: "Papiery CE/kierowców blokują wyjazd." },
      { en: "Ops and recruiters use different trackers.", ru: "Операции и рекрутинг в разных таблицах.", pl: "Ops i rekrutacja w różnych trackerach." },
      { en: "High volume makes follow-ups disappear.", ru: "При большом потоке пропадают follow-up.", pl: "Przy dużym wolumenie giną follow-upy." },
    ],
    solutionTitle: { en: "One operating rhythm", ru: "Один операционный ритм", pl: "Jeden rytm operacyjny" },
    solutionBody: { en: "HostFlow connects ads → vacancy → recruiter → documents so transport teams see blockers before they cost a trip.", ru: "HostFlow связывает рекламу → вакансию → рекрутера → документы — блокеры видны до потери рейса.", pl: "HostFlow łączy reklamy → wakat → rekrutera → dokumenty — blokery widać zanim kosztują wyjazd." },
    flowTitle: { en: "Recommended flow", ru: "Рекомендуемый поток", pl: "Zalecany przepływ" },
    flowItems: [
      { en: "Open vacancies for drivers and warehouse roles.", ru: "Откройте вакансии водителей и склада.", pl: "Otwórz wakaty kierowców i magazynu." },
      { en: "Ingest Meta and form applications automatically.", ru: "Автоматически принимайте заявки Meta и форм.", pl: "Automatycznie przyjmuj zgłoszenia Meta i formularzy." },
      { en: "Qualify, contact, and move stages with owners.", ru: "Квалифицируйте, звоните и двигайте этапы с владельцами.", pl: "Kwalifikuj, kontaktuj i przesuwaj etapy z właścicielami." },
      { en: "Clear document red flags before onboarding.", ru: "Снимайте красные документы до онбординга.", pl: "Usuń czerwone dokumenty przed onboardingiem." },
    ],
    faq: [
      {
        q: { en: "Is this only for drivers?", ru: "Только для водителей?", pl: "Tylko dla kierowców?" },
        a: { en: "No — any high-volume transport role with documents and stages.", ru: "Нет — любая роль с потоком, документами и этапами.", pl: "Nie — każda rola z wolumenem, dokumentami i etapami." },
      },
      {
        q: { en: "Can fleet/ops see hiring status?", ru: "Видит ли флит/ops статус найма?", pl: "Czy fleet/ops widzi status rekrutacji?" },
        a: { en: "Shared pipeline and document states keep ops aligned.", ru: "Общий пайплайн и статусы документов выравнивают ops.", pl: "Wspólny pipeline i statusy dokumentów ustawiają ops." },
      },
      {
        q: { en: "Do we need ATS plus CRM?", ru: "Нужен ли ещё ATS плюс CRM?", pl: "Czy potrzeba ATS plus CRM?" },
        a: { en: "HostFlow covers operational tracking; start CRM-first.", ru: "HostFlow закрывает операционный трекинг; начинайте с CRM.", pl: "HostFlow pokrywa tracking operacyjny; zacznij od CRM." },
      },
    ],
    related: [
      { path: "/use-cases/trucking-recruitment", label: { en: "Trucking recruitment", ru: "Рекрутинг водителей", pl: "Rekrutacja kierowców" } },
      { path: "/features/document-control", label: { en: "Document control", ru: "Контроль документов", pl: "Kontrola dokumentów" } },
      { path: "/use-cases/ats-for-transport", label: { en: "ATS for transport", ru: "ATS для транспорта", pl: "ATS dla transportu" } },
      { path: "/faq", label: { en: "FAQ", ru: "FAQ", pl: "FAQ" } },
    ],
  },
  {
    id: "driver_recruitment",
    path: "/use-cases/driver-recruitment",
    pageType: "use_case",
    badge: { en: "Use-case", ru: "Сценарий", pl: "Use-case" },
    seoTitle: { en: "CRM for Driver Recruitment | HostFlow", ru: "CRM для рекрутинга водителей | HostFlow", pl: "CRM do rekrutacji kierowców | HostFlow" },
    seoDescription: { en: "Driver recruitment CRM: Meta leads, CE document checks, stage ownership, and reminders so vacancies close faster.", ru: "CRM рекрутинга водителей: лиды Meta, проверка CE-документов, этапы и напоминания — вакансии закрываются быстрее.", pl: "CRM rekrutacji kierowców: leady Meta, kontrola dokumentów CE, etapy i przypomnienia — wakaty zamykane szybciej." },
    h1: { en: "CRM for Driver Recruitment", ru: "CRM для рекрутинга водителей", pl: "CRM do rekrutacji kierowców" },
    subtitle: { en: "Turn driver applications into dispatched hires without spreadsheet chaos.", ru: "Превращайте заявки водителей в выходы без хаоса таблиц.", pl: "Zamieniaj zgłoszenia kierowców na wyjazdy bez chaosu arkuszy." },
    problemTitle: { en: "Why driver hiring stalls", ru: "Почему стопорится найм водителей", pl: "Dlaczego stoi rekrutacja kierowców" },
    problemItems: [
      { en: "Applications arrive faster than follow-up.", ru: "Заявки приходят быстрее, чем follow-up.", pl: "Zgłoszenia przychodzą szybciej niż follow-up." },
      { en: "License and permit gaps surface too late.", ru: "Пробелы в правах/разрешениях всплывают поздно.", pl: "Braki w prawie/zezwoleniach wychodzą za późno." },
      { en: "No single view of who is ready to drive.", ru: "Нет единого вида, кто готов к рейсу.", pl: "Brak jednego widoku, kto jest gotowy do jazdy." },
    ],
    solutionTitle: { en: "Driver-ready pipeline", ru: "Пайплайн «готов к рейсу»", pl: "Pipeline «gotowy do jazdy»" },
    solutionBody: { en: "HostFlow keeps leads, stages, and documents on one vacancy so recruiters know the next call and ops know readiness.", ru: "HostFlow держит лиды, этапы и документы на одной вакансии — рекрутер знает следующий звонок, ops — готовность.", pl: "HostFlow trzyma leady, etapy i dokumenty na jednym wakacie — rekruter zna kolejny telefon, ops — gotowość." },
    flowTitle: { en: "From ad to ready driver", ru: "От рекламы до готового водителя", pl: "Od reklamy do gotowego kierowcy" },
    flowItems: [
      { en: "Map Meta forms to driver vacancies.", ru: "Привяжите формы Meta к вакансиям водителей.", pl: "Zmapuj formularze Meta do wakatów kierowców." },
      { en: "Qualify and contact with clear ownership.", ru: "Квалифицируйте и звоните с ясным владельцем.", pl: "Kwalifikuj i kontaktuj z jasnym ownership." },
      { en: "Collect CE/ID/permit files with status.", ru: "Собирайте CE/ID/разрешения со статусами.", pl: "Zbieraj pliki CE/ID/zezwoleń ze statusami." },
      { en: "Hand off only when documents are green.", ru: "Передавайте дальше только с зелёными документами.", pl: "Przekazuj dalej dopiero przy zielonych dokumentach." },
    ],
    faq: [
      {
        q: { en: "Does it support CE truck drivers?", ru: "Подходит для CE?", pl: "Czy wspiera CE?" },
        a: { en: "Yes — document-heavy driver flows are a core use-case.", ru: "Да — документный найм водителей — ключевой сценарий.", pl: "Tak — rekrutacja kierowców z dokumentami to kluczowy scenariusz." },
      },
      {
        q: { en: "Can we hire EU and non-EU drivers?", ru: "Можно EU и non-EU?", pl: "Czy EU i non-EU?" },
        a: { en: "Yes. Track permits and readiness per candidate.", ru: "Да. Ведите разрешения и готовность по кандидату.", pl: "Tak. Śledź zezwolenia i gotowość per kandydat." },
      },
      {
        q: { en: "Where do I start?", ru: "С чего начать?", pl: "Od czego zacząć?" },
        a: { en: "Create a driver vacancy, connect Meta, process the first lead.", ru: "Создайте вакансию водителя, подключите Meta, обработайте первый лид.", pl: "Utwórz wakat kierowcy, podłącz Meta, obsłuż pierwszy lead." },
      },
    ],
    related: [
      { path: "/use-cases/trucking-recruitment", label: { en: "Trucking recruitment", ru: "Рекрутинг в траке", pl: "Rekrutacja trucking" } },
      { path: "/use-cases/ats-for-drivers", label: { en: "ATS for drivers", ru: "ATS для водителей", pl: "ATS dla kierowców" } },
      { path: "/features/document-control", label: { en: "Document control", ru: "Контроль документов", pl: "Kontrola dokumentów" } },
      { path: "/faq", label: { en: "FAQ", ru: "FAQ", pl: "FAQ" } },
    ],
  },
  {
    id: "whatsapp_recruitment",
    path: "/features/whatsapp-recruitment",
    pageType: "feature",
    badge: { en: "Feature", ru: "Функция", pl: "Feature" },
    seoTitle: { en: "Recruitment CRM with WhatsApp | HostFlow", ru: "Recruitment CRM с WhatsApp | HostFlow", pl: "CRM rekrutacyjny z WhatsApp | HostFlow" },
    seoDescription: { en: "Keep candidate WhatsApp conversations next to pipeline stages and ownership — less switching, fewer lost follow-ups.", ru: "Переписка WhatsApp с кандидатами рядом с этапами и владельцем — меньше переключений и потерянных follow-up.", pl: "Rozmowy WhatsApp z kandydatami obok etapów i ownership — mniej przełączeń i utraconych follow-upów." },
    h1: { en: "CRM with WhatsApp for hiring teams", ru: "CRM с WhatsApp для команд найма", pl: "CRM z WhatsApp dla zespołów rekrutacji" },
    subtitle: { en: "Chat where the work already lives — leads, candidates, and next actions in one system.", ru: "Общайтесь там, где уже идёт работа — лиды, кандидаты и следующие шаги в одной системе.", pl: "Rozmawiaj tam, gdzie jest praca — leady, kandydaci i kolejne kroki w jednym systemie." },
    problemTitle: { en: "WhatsApp without CRM context", ru: "WhatsApp без контекста CRM", pl: "WhatsApp bez kontekstu CRM" },
    problemItems: [
      { en: "Chats live on personal phones.", ru: "Чаты на личных телефонах.", pl: "Czaty na prywatnych telefonach." },
      { en: "Nobody sees who was answered.", ru: "Не видно, кому ответили.", pl: "Nikt nie widzi, komu odpowiedziano." },
      { en: "Pipeline stages drift from the conversation.", ru: "Этапы пайплайна расходятся с перепиской.", pl: "Etapy pipeline rozjeżdżają się z rozmową." },
    ],
    solutionTitle: { en: "Messaging inside the hiring workflow", ru: "Переписка внутри процесса найма", pl: "Wiadomości w procesie rekrutacji" },
    solutionBody: { en: "When WhatsApp channels are on your plan, conversations attach to people in HostFlow so the next action stays visible.", ru: "Когда WhatsApp в тарифе, переписка привязана к людям в HostFlow — следующий шаг остаётся видимым.", pl: "Gdy WhatsApp jest w planie, rozmowy są powiązane z osobami w HostFlow — kolejny krok zostaje widoczny." },
    flowTitle: { en: "How teams use it", ru: "Как этим пользуются", pl: "Jak zespoły z tego korzystają" },
    flowItems: [
      { en: "Connect a WhatsApp channel in Communications.", ru: "Подключите канал WhatsApp в Communications.", pl: "Podłącz kanał WhatsApp w Communications." },
      { en: "Link threads to leads or candidates.", ru: "Свяжите треды с лидами или кандидатами.", pl: "Powiąż wątki z leadami lub kandydatami." },
      { en: "Update stage after contact — same screen family.", ru: "Обновите этап после контакта — в том же контуре.", pl: "Zaktualizuj etap po kontakcie — w tym samym konturze." },
      { en: "Use reminders when a reply is due.", ru: "Ставьте напоминания, когда нужен ответ.", pl: "Ustaw przypomnienia, gdy potrzebna odpowiedź." },
    ],
    faq: [
      {
        q: { en: "Is WhatsApp required to use HostFlow?", ru: "Обязателен ли WhatsApp?", pl: "Czy WhatsApp jest wymagany?" },
        a: { en: "No. Start with Meta forms and add WhatsApp when you need chat.", ru: "Нет. Начните с форм Meta и добавьте WhatsApp для чата.", pl: "Nie. Zacznij od formularzy Meta i dodaj WhatsApp do czatu." },
      },
      {
        q: { en: "Are there plan limits?", ru: "Есть ли лимиты тарифа?", pl: "Czy są limity planu?" },
        a: { en: "Yes — channel limits follow your plan. See Pricing.", ru: "Да — лимиты каналов по тарифу. См. Pricing.", pl: "Tak — limity kanałów wg planu. Zobacz Pricing." },
      },
      {
        q: { en: "Can we use templates?", ru: "Можно ли шаблоны?", pl: "Czy można szablony?" },
        a: { en: "Provider/Meta template rules apply outside the service window.", ru: "Вне окна обслуживания действуют шаблоны провайдера/Meta.", pl: "Poza oknem obsługi obowiązują szablony dostawcy/Meta." },
      },
    ],
    related: [
      { path: "/features/meta-ads-recruitment", label: { en: "Meta ads intake", ru: "Лиды Meta", pl: "Intake Meta" } },
      { path: "/features/candidate-pipeline", label: { en: "Candidate pipeline", ru: "Пайплайн", pl: "Pipeline" } },
      { path: "/faq#whatsapp", label: { en: "WhatsApp FAQ", ru: "FAQ WhatsApp", pl: "FAQ WhatsApp" } },
      { path: "/pricing", label: { en: "Pricing", ru: "Тарифы", pl: "Cennik" } },
    ],
  },
  {
    id: "meta_ads_recruitment",
    path: "/features/meta-ads-recruitment",
    pageType: "feature",
    badge: { en: "Feature", ru: "Функция", pl: "Feature" },
    seoTitle: { en: "Recruitment CRM with Meta Ads | HostFlow", ru: "Recruitment CRM с Meta Ads | HostFlow", pl: "CRM rekrutacyjny z Meta Ads | HostFlow" },
    seoDescription: { en: "Connect Facebook/Instagram lead forms to HostFlow vacancies — applications arrive owned, staged, and ready to contact.", ru: "Подключите формы Facebook/Instagram к вакансиям HostFlow — заявки приходят с владельцем, этапом и готовы к контакту.", pl: "Podłącz formularze Facebook/Instagram do wakatów HostFlow — zgłoszenia przychodzą z ownership, etapem i gotowe do kontaktu." },
    h1: { en: "Recruitment CRM with Meta Ads", ru: "Recruitment CRM с Meta Ads", pl: "CRM rekrutacyjny z Meta Ads" },
    subtitle: { en: "Stop copying leads from Ads Manager — map forms once and process every application in the pipeline.", ru: "Хватит копировать лиды из Ads Manager — один раз привяжите формы и обрабатывайте заявки в пайплайне.", pl: "Koniec kopiowania leadów z Ads Manager — raz zmapuj formularze i obsługuj zgłoszenia w pipeline." },
    problemTitle: { en: "Ads without operational CRM", ru: "Реклама без операционной CRM", pl: "Reklamy bez operacyjnego CRM" },
    problemItems: [
      { en: "Leads export to sheets and die there.", ru: "Лиды уходят в таблицы и там умирают.", pl: "Leady idą do arkuszy i tam umierają." },
      { en: "No vacancy context on the first call.", ru: "На первом звонке нет контекста вакансии.", pl: "Przy pierwszym telefonie brak kontekstu wakatu." },
      { en: "Spend continues while follow-up is blind.", ru: "Бюджет крутится, а follow-up слепой.", pl: "Budżet leci, a follow-up jest ślepy." },
    ],
    solutionTitle: { en: "Meta → vacancy → recruiter", ru: "Meta → вакансия → рекрутер", pl: "Meta → wakat → rekruter" },
    solutionBody: { en: "HostFlow connects Meta so each lead lands on the right vacancy with ownership and a clear next action.", ru: "HostFlow подключает Meta так, что каждый лид попадает на нужную вакансию с владельцем и следующим шагом.", pl: "HostFlow łączy Meta tak, że każdy lead trafia na właściwy wakat z ownership i jasnym kolejnym krokiem." },
    flowTitle: { en: "Setup in minutes", ru: "Настройка за минуты", pl: "Konfiguracja w minuty" },
    flowItems: [
      { en: "Connect Meta in Integrations.", ru: "Подключите Meta в Интеграциях.", pl: "Podłącz Meta w Integracjach." },
      { en: "Map forms or ads to vacancies.", ru: "Привяжите формы/объявления к вакансиям.", pl: "Zmapuj formularze/reklamy do wakatów." },
      { en: "Send a test lead and confirm inbox.", ru: "Отправьте тестовый лид и проверьте inbox.", pl: "Wyślij testowy lead i sprawdź inbox." },
      { en: "Contact and convert to candidates.", ru: "Свяжитесь и переведите в кандидаты.", pl: "Skontaktuj się i przenieś do kandydatów." },
    ],
    faq: [
      {
        q: { en: "Which plans support Meta OAuth?", ru: "На каких тарифах OAuth Meta?", pl: "Które plany mają OAuth Meta?" },
        a: { en: "Quick OAuth from Team upward; see Pricing for Solo limits.", ru: "Быстрый OAuth с Team; лимиты Solo — на Pricing.", pl: "Szybki OAuth od Team; limity Solo — na Pricing." },
      },
      {
        q: { en: "Why aren’t leads arriving?", ru: "Почему не приходят лиды?", pl: "Dlaczego nie ma leadów?" },
        a: { en: "Check connection, form mapping, active ads, and plan caps — see FAQ Meta section.", ru: "Проверьте подключение, маппинг, активные объявления и капы — раздел FAQ Meta.", pl: "Sprawdź połączenie, mapping, aktywne reklamy i limity — sekcja FAQ Meta." },
      },
      {
        q: { en: "Can we use multiple ad accounts?", ru: "Несколько ad account?", pl: "Wiele kont reklam?" },
        a: { en: "Yes within plan and permission limits of the connected Business.", ru: "Да в рамках тарифа и прав подключённого Business.", pl: "Tak w ramach planu i uprawnień podłączonego Business." },
      },
    ],
    related: [
      { path: "/features/whatsapp-recruitment", label: { en: "WhatsApp hiring", ru: "WhatsApp в найме", pl: "WhatsApp w rekrutacji" } },
      { path: "/use-cases/recruitment-agencies", label: { en: "Agencies", ru: "Агентства", pl: "Agencje" } },
      { path: "/faq#meta", label: { en: "Meta FAQ", ru: "FAQ Meta", pl: "FAQ Meta" } },
      { path: "/signup", label: { en: "Create account", ru: "Создать аккаунт", pl: "Utwórz konto" } },
    ],
  },
  {
    id: "ats_for_drivers",
    path: "/use-cases/ats-for-drivers",
    pageType: "use_case",
    badge: { en: "Use-case", ru: "Сценарий", pl: "Use-case" },
    seoTitle: { en: "ATS for Drivers | HostFlow", ru: "ATS для водителей | HostFlow", pl: "ATS dla kierowców | HostFlow" },
    seoDescription: { en: "Applicant tracking for driver hiring in Europe — stages, documents, and Meta intake in an operations-first ATS/CRM.", ru: "ATS найма водителей в Европе — этапы, документы и Meta в операционном ATS/CRM.", pl: "ATS rekrutacji kierowców w Europie — etapy, dokumenty i Meta w operacyjnym ATS/CRM." },
    h1: { en: "ATS for Drivers", ru: "ATS для водителей", pl: "ATS dla kierowców" },
    subtitle: { en: "Track every driver application from form to hire with operational control — not just an applicant list.", ru: "Ведите каждую заявку водителя от формы до найма с операционным контролем — не просто список applicants.", pl: "Prowadź każde zgłoszenie kierowcy od formularza do zatrudnienia z kontrolą operacyjną — nie tylko listą applicants." },
    problemTitle: { en: "Classic ATS gaps for drivers", ru: "Пробелы классического ATS для водителей", pl: "Luki klasycznego ATS dla kierowców" },
    problemItems: [
      { en: "ATS stores applications but not daily follow-up.", ru: "ATS хранит заявки, но не ежедневный follow-up.", pl: "ATS trzyma zgłoszenia, ale nie codzienny follow-up." },
      { en: "Document readiness is a side spreadsheet.", ru: "Готовность документов — в соседней таблице.", pl: "Gotowość dokumentów — w osobnym arkuszu." },
      { en: "Ad spend is disconnected from stages.", ru: "Рекламный бюджет оторван от этапов.", pl: "Budżet reklam oderwany od etapów." },
    ],
    solutionTitle: { en: "ATS speed + CRM operations", ru: "Скорость ATS + операции CRM", pl: "Szybkość ATS + operacje CRM" },
    solutionBody: { en: "HostFlow combines applicant tracking with recruiter ownership, Meta intake, and document control for driver roles.", ru: "HostFlow совмещает трекинг заявок с ответственностью рекрутера, Meta и контролем документов для водителей.", pl: "HostFlow łączy tracking zgłoszeń z ownership rekrutera, Meta i kontrolą dokumentów dla kierowców." },
    flowTitle: { en: "Driver ATS path", ru: "Путь driver ATS", pl: "Ścieżka ATS kierowcy" },
    flowItems: [
      { en: "Ingest applications into a driver vacancy.", ru: "Принимайте заявки на вакансию водителя.", pl: "Przyjmuj zgłoszenia na wakat kierowcy." },
      { en: "Stage with SLA reminders.", ru: "Этапы с напоминаниями SLA.", pl: "Etapy z przypomnieniami SLA." },
      { en: "Verify documents before offer/dispatch.", ru: "Проверяйте документы до оффера/выхода.", pl: "Weryfikuj dokumenty przed ofertą/wyjazdem." },
      { en: "Report bottlenecks to managers.", ru: "Показывайте узкие места менеджерам.", pl: "Pokazuj wąskie gardła managerom." },
    ],
    faq: [
      {
        q: { en: "Is HostFlow an ATS or a CRM?", ru: "HostFlow — ATS или CRM?", pl: "HostFlow to ATS czy CRM?" },
        a: { en: "Operations CRM with ATS-like tracking — see also CRM vs ATS.", ru: "Операционная CRM с ATS-трекингом — см. CRM vs ATS.", pl: "Operacyjny CRM z trackingiem ATS — zobacz CRM vs ATS." },
      },
      {
        q: { en: "Europe-focused?", ru: "Фокус на Европе?", pl: "Skupienie na Europie?" },
        a: { en: "Built for EU hiring flows including permits and multi-country teams.", ru: "Под EU-найм: разрешения и мультистрановые команды.", pl: "Pod rekrutację UE: zezwolenia i zespoły wielokrajowe." },
      },
      {
        q: { en: "Can we migrate from sheets?", ru: "Можно уйти с таблиц?", pl: "Czy odejść od arkuszy?" },
        a: { en: "Yes — start with one vacancy and connect intake.", ru: "Да — начните с одной вакансии и подключите intake.", pl: "Tak — zacznij od jednego wakatu i podłącz intake." },
      },
    ],
    related: [
      { path: "/comparison/recruitment-crm-vs-ats", label: { en: "CRM vs ATS", ru: "CRM vs ATS", pl: "CRM vs ATS" } },
      { path: "/use-cases/driver-recruitment", label: { en: "Driver recruitment CRM", ru: "CRM рекрутинга водителей", pl: "CRM rekrutacji kierowców" } },
      { path: "/use-cases/ats-europe", label: { en: "ATS Europe", ru: "ATS Европа", pl: "ATS Europa" } },
      { path: "/faq", label: { en: "FAQ", ru: "FAQ", pl: "FAQ" } },
    ],
  },
  {
    id: "ats_for_transport",
    path: "/use-cases/ats-for-transport",
    pageType: "use_case",
    badge: { en: "Use-case", ru: "Сценарий", pl: "Use-case" },
    seoTitle: { en: "ATS for Transport | HostFlow", ru: "ATS для транспорта | HostFlow", pl: "ATS dla transportu | HostFlow" },
    seoDescription: { en: "Applicant tracking for transport hiring teams — warehouse and driver roles with pipeline, documents, and ad intake.", ru: "ATS для транспортного найма — склад и водители с пайплайном, документами и рекламным intake.", pl: "ATS dla rekrutacji transportowej — magazyn i kierowcy z pipeline, dokumentami i intake z reklam." },
    h1: { en: "ATS for Transport", ru: "ATS для транспорта", pl: "ATS dla transportu" },
    subtitle: { en: "One tracking system for every transport vacancy — from application to operational readiness.", ru: "Одна система трекинга для каждой транспортной вакансии — от заявки до операционной готовности.", pl: "Jeden system trackingu dla każdego wakatu transportowego — od zgłoszenia do gotowości operacyjnej." },
    problemTitle: { en: "Transport ATS requirements", ru: "Требования транспортного ATS", pl: "Wymagania ATS transportu" },
    problemItems: [
      { en: "Multiple role types, one chaotic inbox.", ru: "Много ролей — один хаотичный inbox.", pl: "Wiele ról — jeden chaotyczny inbox." },
      { en: "Ops needs readiness, not just HR records.", ru: "Ops нужна готовность, не только HR-учёт.", pl: "Ops potrzebuje gotowości, nie tylko ewidencji HR." },
      { en: "Agencies and in-house teams need shared status.", ru: "Агентствам и in-house нужен общий статус.", pl: "Agencje i in-house potrzebują wspólnego statusu." },
    ],
    solutionTitle: { en: "Transport-ready tracking", ru: "Трекинг для транспорта", pl: "Tracking pod transport" },
    solutionBody: { en: "HostFlow tracks applicants with vacancy context, ownership, and document gates suited to transport operations.", ru: "HostFlow трекает applicants с контекстом вакансии, владельцем и документными гейтами под транспорт.", pl: "HostFlow trackuje applicants z kontekstem wakatu, ownership i bramkami dokumentów pod transport." },
    flowTitle: { en: "How it runs", ru: "Как это работает", pl: "Jak to działa" },
    flowItems: [
      { en: "Create vacancies per role and site.", ru: "Создайте вакансии по ролям и площадкам.", pl: "Utwórz wakaty wg ról i lokalizacji." },
      { en: "Route Meta/forms into the right vacancy.", ru: "Направьте Meta/формы на нужную вакансию.", pl: "Skieruj Meta/formularze na właściwy wakat." },
      { en: "Process stages with team visibility.", ru: "Ведите этапы с видимостью команды.", pl: "Prowadź etapy z widocznością zespołu." },
      { en: "Unblock documents before start date.", ru: "Снимайте документные блокеры до даты старта.", pl: "Odblokuj dokumenty przed datą startu." },
    ],
    faq: [
      {
        q: { en: "Drivers and warehouse in one ATS?", ru: "Водители и склад в одном ATS?", pl: "Kierowcy i magazyn w jednym ATS?" },
        a: { en: "Yes — separate vacancies, shared operating model.", ru: "Да — разные вакансии, общая операционная модель.", pl: "Tak — osobne wakaty, wspólny model operacyjny." },
      },
      {
        q: { en: "Agency mode supported?", ru: "Режим агентства?", pl: "Tryb agencji?" },
        a: { en: "Yes — client companies and vacancies keep context clear.", ru: "Да — клиентские компании и вакансии держат контекст.", pl: "Tak — firmy klientów i wakaty trzymają kontekst." },
      },
      {
        q: { en: "Compare to spreadsheets?", ru: "Сравнение с таблицами?", pl: "Porównanie z arkuszami?" },
        a: { en: "See HostFlow vs spreadsheets.", ru: "См. HostFlow vs spreadsheets.", pl: "Zobacz HostFlow vs spreadsheets." },
      },
    ],
    related: [
      { path: "/use-cases/transport-companies", label: { en: "Transport companies CRM", ru: "CRM для транспорта", pl: "CRM firm transportowych" } },
      { path: "/comparison/hostflow-vs-spreadsheets", label: { en: "Vs spreadsheets", ru: "Vs таблицы", pl: "Vs arkusze" } },
      { path: "/features/candidate-pipeline", label: { en: "Pipeline", ru: "Пайплайн", pl: "Pipeline" } },
      { path: "/faq", label: { en: "FAQ", ru: "FAQ", pl: "FAQ" } },
    ],
  },
  {
    id: "ats_europe",
    path: "/use-cases/ats-europe",
    pageType: "use_case",
    badge: { en: "Use-case", ru: "Сценарий", pl: "Use-case" },
    seoTitle: { en: "Applicant Tracking System Europe | HostFlow", ru: "Applicant Tracking System Europe | HostFlow", pl: "Applicant Tracking System Europe | HostFlow" },
    seoDescription: { en: "European applicant tracking for operational hiring teams — multi-country pipelines, Meta intake, GDPR-aware workflows.", ru: "Европейский ATS для операционного найма — мультистрановые пайплайны, Meta, GDPR-aware процессы.", pl: "Europejski ATS dla operacyjnej rekrutacji — pipeline wielokrajowe, Meta, procesy GDPR-aware." },
    h1: { en: "Applicant Tracking System for Europe", ru: "Applicant Tracking System для Европы", pl: "Applicant Tracking System dla Europy" },
    subtitle: { en: "Hire across EU markets with one operational ATS/CRM — clear ownership, documents, and compliant communication paths.", ru: "Нанимайте на рынках EU в одном операционном ATS/CRM — ответственность, документы и compliant-коммуникации.", pl: "Rekrutuj na rynkach UE w jednym operacyjnym ATS/CRM — ownership, dokumenty i ścieżki compliant komunikacji." },
    problemTitle: { en: "EU hiring complexity", ru: "Сложность найма в EU", pl: "Złożoność rekrutacji w UE" },
    problemItems: [
      { en: "Candidates cross borders; trackers do not.", ru: "Кандидаты пересекают границы — трекеры нет.", pl: "Kandydaci przekraczają granice — trackery nie." },
      { en: "GDPR notices and stages are manual.", ru: "GDPR-уведомления и этапы вручную.", pl: "Powiadomienia GDPR i etapy ręcznie." },
      { en: "Ads generate volume without EU process control.", ru: "Реклама даёт объём без контроля EU-процесса.", pl: "Reklamy dają wolumen bez kontroli procesu UE." },
    ],
    solutionTitle: { en: "Europe-ready operations", ru: "Операции под Европу", pl: "Operacje pod Europę" },
    solutionBody: { en: "HostFlow gives EU teams applicant tracking plus recruiter execution: intake, stages, documents, and policy-aware messaging.", ru: "HostFlow даёт EU-командам трекинг заявок плюс исполнение рекрутера: intake, этапы, документы и messaging с политиками.", pl: "HostFlow daje zespołom UE tracking zgłoszeń plus egzekucję rekrutera: intake, etapy, dokumenty i messaging z politykami." },
    flowTitle: { en: "EU hiring path", ru: "Путь найма в EU", pl: "Ścieżka rekrutacji UE" },
    flowItems: [
      { en: "Set company country and open vacancies.", ru: "Задайте страну компании и откройте вакансии.", pl: "Ustaw kraj firmy i otwórz wakaty." },
      { en: "Connect Meta / forms for EU campaigns.", ru: "Подключите Meta / формы для EU-кампаний.", pl: "Podłącz Meta / formularze dla kampanii UE." },
      { en: "Run stages with ownership and reminders.", ru: "Ведите этапы с владельцем и напоминаниями.", pl: "Prowadź etapy z ownership i przypomnieniami." },
      { en: "Keep document and communication status visible.", ru: "Держите статусы документов и коммуникаций видимыми.", pl: "Utrzymuj widoczne statusy dokumentów i komunikacji." },
    ],
    faq: [
      {
        q: { en: "Is HostFlow available in Europe?", ru: "HostFlow доступен в Европе?", pl: "Czy HostFlow jest w Europie?" },
        a: { en: "Yes — product and GTM focus on European hiring operations.", ru: "Да — продукт и GTM на европейском операционном найме.", pl: "Tak — produkt i GTM na europejskiej rekrutacji operacyjnej." },
      },
      {
        q: { en: "GDPR support?", ru: "Поддержка GDPR?", pl: "Wsparcie GDPR?" },
        a: { en: "Tenant isolation, RBAC, and configurable lead notices — see FAQ Security.", ru: "Изоляция tenant, RBAC и настраиваемые уведомления — FAQ Security.", pl: "Izolacja tenanta, RBAC i konfigurowalne powiadomienia — FAQ Security." },
      },
      {
        q: { en: "Languages?", ru: "Языки?", pl: "Języki?" },
        a: { en: "Product UI supports EN/RU/PL with more locales evolving.", ru: "UI: EN/RU/PL, локали расширяются.", pl: "UI: EN/RU/PL, locale się rozwijają." },
      },
    ],
    related: [
      { path: "/use-cases/ats-for-drivers", label: { en: "ATS for drivers", ru: "ATS для водителей", pl: "ATS dla kierowców" } },
      { path: "/use-cases/recruitment-agencies", label: { en: "Agencies", ru: "Агентства", pl: "Agencje" } },
      { path: "/faq#security", label: { en: "Security FAQ", ru: "FAQ Security", pl: "FAQ Security" } },
      { path: "/pricing", label: { en: "Pricing", ru: "Тарифы", pl: "Cennik" } },
    ],
  },
]

export function seoLocaleFromApp(locale: string | undefined): SeoLocale {
  if (!locale) return 'en'
  if (locale.startsWith('ru')) return 'ru'
  if (locale.startsWith('pl')) return 'pl'
  return 'en'
}

export function getSeoPageByPath(pathname: string): SeoPageDefinition | undefined {
  return SEO_PAGE_CATALOG.find((page) => page.path === pathname)
}

export function getSeoPageById(id: string): SeoPageDefinition | undefined {
  return SEO_PAGE_CATALOG.find((page) => page.id === id)
}

