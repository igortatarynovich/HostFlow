/** FAQ catalog — Growth /faq hub (ADR-034). Locales: en, ru, pl. */

export type FaqLocale = 'en' | 'ru' | 'pl'

export type FaqText = Record<FaqLocale, string>

export type FaqItem = {
  id: string
  q: FaqText
  a: FaqText
}

export type FaqSection = {
  id: string
  title: FaqText
  items: FaqItem[]
}

export const FAQ_SECTIONS: FaqSection[] = [
  {
    id: "getting_started",
    title: { en: "Getting started", ru: "Начало работы", pl: "Pierwsze kroki" },
    items: [
      {
        id: "register",
        q: { en: "How do I register?", ru: "Как зарегистрироваться?", pl: "Jak się zarejestrować?" },
        a: { en: "Open hostflow.cc, click Start free setup / Create workspace, enter email and password. After signup you create your company and follow the next step on screen.", ru: "Откройте hostflow.cc, нажмите «Начать настройку», укажите email и пароль. После регистрации создайте компанию и сделайте следующий шаг на экране.", pl: "Wejdź na hostflow.cc, kliknij start konfiguracji, podaj email i hasło. Po rejestracji utwórz firmę i wykonaj kolejny krok na ekranie." },
      },
      {
        id: "confirm_email",
        q: { en: "Do I need to confirm email?", ru: "Нужно ли подтверждать email?", pl: "Czy trzeba potwierdzić email?" },
        a: { en: "If confirmation is enabled for your environment, follow the link in the email before full access. In trial self-serve you usually continue after signup immediately.", ru: "Если подтверждение включено в окружении — перейдите по ссылке из письма. В self-serve trial обычно можно продолжать сразу после регистрации.", pl: "Jeśli potwierdzenie jest włączone — kliknij link z maila. W trial self-serve zwykle kontynuujesz od razu po rejestracji." },
      },
      {
        id: "create_company",
        q: { en: "How do I create a company?", ru: "Как создать компанию?", pl: "Jak utworzyć firmę?" },
        a: { en: "After signup HostFlow opens a short company form (name, country, activity). That is required once — then you work in the normal product with a clear next step.", ru: "После регистрации откроется короткая форма компании (название, страна, деятельность). Это один раз — дальше обычный продукт с понятным следующим шагом.", pl: "Po rejestracji pojawi się krótki formularz firmy (nazwa, kraj, działalność). To raz — potem zwykły produkt z jasnym kolejnym krokiem." },
      },
      {
        id: "invite_team",
        q: { en: "How do I invite teammates?", ru: "Как пригласить сотрудников?", pl: "Jak zaprosić zespół?" },
        a: { en: "Go to Settings → Users (or Team) and send invites. Inviting is optional — you can hire solo first and add people later.", ru: "Настройки → Пользователи (или Команда) — отправьте приглашения. Это необязательно: можно начать одному и добавить людей позже.", pl: "Ustawienia → Użytkownicy (lub Zespół) — wyślij zaproszenia. To opcjonalne: możesz zacząć solo i dodać ludzi później." },
      },
      {
        id: "first_value",
        q: { en: "What is the fastest path to first value?", ru: "Как быстрее всего получить первую ценность?", pl: "Jaka jest najszybsza droga do pierwszej wartości?" },
        a: { en: "Create company → create a vacancy → connect Meta ads (or skip) → receive a lead → contact them. The Getting started checklist always shows the single next action.", ru: "Компания → вакансия → Meta (или позже) → заявка → контакт. Чек-лист «Старт» всегда показывает один следующий шаг.", pl: "Firma → wakat → Meta (lub później) → lead → kontakt. Checklista startu zawsze pokazuje jeden kolejny krok." },
      },
      {
        id: "no_support",
        q: { en: "Can I start without talking to sales or support?", ru: "Можно ли начать без поддержки и sales?", pl: "Czy mogę zacząć bez supportu i sales?" },
        a: { en: "Yes. Self-serve signup, company setup, vacancy, and Meta connect are designed so you reach first value without a call.", ru: "Да. Регистрация, компания, вакансия и Meta рассчитаны на самостоятельный старт без звонка.", pl: "Tak. Rejestracja, firma, wakat i Meta są zaprojektowane pod start bez rozmowy." },
      },
    ],
  },
  {
    id: "meta",
    title: { en: "Meta / Facebook ads", ru: "Meta / Facebook реклама", pl: "Meta / reklamy Facebook" },
    items: [
      {
        id: "connect_meta",
        q: { en: "How do I connect Meta?", ru: "Как подключить Meta?", pl: "Jak podłączyć Meta?" },
        a: { en: "Open Settings → Integrations → Meta and use Connect. You need a Meta Business account and permission to the ad account / page that owns the lead forms.", ru: "Настройки → Интеграции → Meta → Connect. Нужен Meta Business и доступ к рекламному кабинету / странице с формами лидов.", pl: "Ustawienia → Integracje → Meta → Connect. Potrzebujesz Meta Business i dostęp do konta reklam / strony z formularzami." },
      },
      {
        id: "campaigns_missing",
        q: { en: "Why don’t I see campaigns?", ru: "Почему не видны кампании?", pl: "Dlaczego nie widzę kampanii?" },
        a: { en: "Usually the wrong ad account is selected, the token lacks ads_read / leads permissions, or campaigns are in another Business Manager. Re-check the connected account and reconnect if needed.", ru: "Чаще выбран другой ad account, у токена нет прав ads_read/leads, или кампании в другом Business Manager. Проверьте аккаунт и переподключите.", pl: "Zwykle wybrano inne konto reklam, brak uprawnień ads_read/leads albo kampanie w innym BM. Sprawdź konto i podłącz ponownie." },
      },
      {
        id: "app_review",
        q: { en: "Why does Meta ask for confirmation / App Review?", ru: "Почему Meta просит подтверждение / App Review?", pl: "Dlaczego Meta prosi o potwierdzenie / App Review?" },
        a: { en: "Meta may ask the admin to approve the HostFlow app or permissions for lead retrieval. An admin of the Business/Page must accept the request.", ru: "Meta может попросить админа одобрить приложение HostFlow или права на лиды. Подтвердить должен админ Business/страницы.", pl: "Meta może poprosić admina o akceptację aplikacji HostFlow lub uprawnień do leadów. Potwierdza admin Business/strony." },
      },
      {
        id: "leads_not_arriving",
        q: { en: "Why aren’t leads arriving?", ru: "Почему не приходят лиды?", pl: "Dlaczego nie przychodzą leady?" },
        a: { en: "Check: Meta connected, form mapped to a vacancy/intake, lead form is active, and test lead sent from Meta. Also verify plan limits and that the ad is delivering.", ru: "Проверьте: Meta подключена, форма привязана к вакансии/intake, форма активна, тестовый лид из Meta ушёл. Также лимиты тарифа и что объявление крутится.", pl: "Sprawdź: Meta podłączona, formularz zmapowany do wakatu/intake, formularz aktywny, testowy lead z Meta. Także limity planu i czy reklama działa." },
      },
      {
        id: "map_form",
        q: { en: "How do I map a lead form to a vacancy?", ru: "Как привязать форму к вакансии?", pl: "Jak zmapować formularz do wakatu?" },
        a: { en: "In Meta integrations, map the form (or ad) to the vacancy / intake route so new leads open in the right hiring context.", ru: "В интеграциях Meta привяжите форму (или объявление) к вакансии / маршруту intake — новые лиды попадут в нужный контекст.", pl: "W integracji Meta zmapuj formularz (lub reklamę) do wakatu / trasy intake — nowe leady trafią we właściwy kontekst." },
      },
      {
        id: "oauth_plan",
        q: { en: "Is Meta OAuth available on every plan?", ru: "OAuth Meta есть на всех тарифах?", pl: "Czy OAuth Meta jest na każdym planie?" },
        a: { en: "Quick OAuth connect is available from Team plan upward. Solo can use Meta with limits; see Pricing / plans matrix for details.", ru: "Быстрый OAuth — с тарифа Team и выше. Solo может использовать Meta с лимитами; детали — в Pricing / матрице тарифов.", pl: "Szybki OAuth — od planu Team w górę. Solo może używać Meta z limitami; szczegóły w Pricing / matrycy planów." },
      },
    ],
  },
  {
    id: "whatsapp",
    title: { en: "WhatsApp", ru: "WhatsApp", pl: "WhatsApp" },
    items: [
      {
        id: "connect_wa",
        q: { en: "How do I connect WhatsApp?", ru: "Как подключить WhatsApp?", pl: "Jak podłączyć WhatsApp?" },
        a: { en: "WhatsApp is connected through HostFlow Communications / channel settings when your plan includes messaging channels. Follow the in-product Connect flow for the provider.", ru: "WhatsApp подключается через Communications / настройки каналов, если тариф включает messaging. Следуйте Connect в продукте.", pl: "WhatsApp łączysz w Communications / ustawieniach kanałów, jeśli plan obejmuje messaging. Postępuj według Connect w produkcie." },
      },
      {
        id: "wa_limits",
        q: { en: "What are WhatsApp limitations?", ru: "Какие ограничения у WhatsApp?", pl: "Jakie są ograniczenia WhatsApp?" },
        a: { en: "Provider and Meta policies apply (templates, 24h session windows, quality rating). HostFlow also applies plan channel limits.", ru: "Действуют правила провайдера и Meta (шаблоны, окно 24ч, quality). Плюс лимиты каналов по тарифу HostFlow.", pl: "Obowiązują reguły dostawcy i Meta (szablony, okno 24h, quality). Plus limity kanałów planu HostFlow." },
      },
      {
        id: "wa_vs_meta",
        q: { en: "Do I need WhatsApp if I already use Meta lead forms?", ru: "Нужен ли WhatsApp, если уже есть формы Meta?", pl: "Czy potrzebuję WhatsApp, jeśli mam formularze Meta?" },
        a: { en: "No. Lead forms cover intake. WhatsApp helps for ongoing chat with candidates after first contact.", ru: "Нет. Формы закрывают сбор заявок. WhatsApp — для переписки с кандидатами после первого контакта.", pl: "Nie. Formularze zbierają zgłoszenia. WhatsApp służy do rozmowy z kandydatami po pierwszym kontakcie." },
      },
      {
        id: "wa_plan",
        q: { en: "Which plan includes WhatsApp channels?", ru: "На каком тарифе есть WhatsApp?", pl: "Który plan obejmuje WhatsApp?" },
        a: { en: "Messaging channels are plan-gated. Compare channel limits on the Pricing page and in Billing.", ru: "Каналы messaging зависят от тарифа. Сравните лимиты на Pricing и в Billing.", pl: "Kanały messaging zależą od planu. Porównaj limity na Pricing i w Billing." },
      },
      {
        id: "wa_templates",
        q: { en: "Can I send free-form WhatsApp messages anytime?", ru: "Можно ли писать в WhatsApp свободно в любой момент?", pl: "Czy mogę pisać na WhatsApp dowolnie w każdej chwili?" },
        a: { en: "Outside the customer-care window you typically need approved templates. HostFlow follows the provider rules.", ru: "Вне окна обслуживания обычно нужны одобренные шаблоны. HostFlow следует правилам провайдера.", pl: "Poza oknem obsługi zwykle potrzebne są zatwierdzone szablony. HostFlow stosuje reguły dostawcy." },
      },
      {
        id: "wa_support",
        q: { en: "Where do WhatsApp conversations appear?", ru: "Где видны переписки WhatsApp?", pl: "Gdzie widać rozmowy WhatsApp?" },
        a: { en: "In the Communications workspace (inbox/threads) linked to the person when identity is resolved.", ru: "В Communications (inbox/треды), привязанных к человеку, когда личность сопоставлена.", pl: "W Communications (inbox/wątki), powiązanych z osobą po dopasowaniu tożsamości." },
      },
    ],
  },
  {
    id: "recruitment",
    title: { en: "Recruitment", ru: "Рекрутинг", pl: "Rekrutacja" },
    items: [
      {
        id: "what_vacancy",
        q: { en: "What is a vacancy?", ru: "Что такое вакансия?", pl: "Czym jest wakat?" },
        a: { en: "A vacancy is the role you hire for. Leads and candidates attach to it so ownership, stages, and documents stay clear.", ru: "Вакансия — роль, на которую вы нанимаете. К ней привязываются лиды и кандидаты: ответственность, этапы и документы.", pl: "Wakat to rola, na którą rekrutujesz. Leady i kandydaci są do niego przypisani: ownership, etapy i dokumenty." },
      },
      {
        id: "create_vacancy",
        q: { en: "How do I create a vacancy?", ru: "Как создать вакансию?", pl: "Jak utworzyć wakat?" },
        a: { en: "Open Vacancies → Create, or use Getting started → Create vacancy. You can finish in about 30 seconds and refine later.", ru: "Вакансии → Создать или Старт → Создать вакансию. Базово — около 30 секунд, детали можно позже.", pl: "Wakaty → Utwórz lub Start → Utwórz wakat. Podstawy w ok. 30 sekund, szczegóły później." },
      },
      {
        id: "what_lead",
        q: { en: "What is a lead?", ru: "Что такое лид?", pl: "Czym jest lead?" },
        a: { en: "A lead is an inbound application or inquiry before it becomes a full candidate in your hiring pipeline.", ru: "Лид — входящая заявка или обращение до перевода в полноценного кандидата в пайплайне.", pl: "Lead to zgłoszenie lub zapytanie przed przeniesieniem do pełnego kandydata w pipeline." },
      },
      {
        id: "what_candidate",
        q: { en: "What is a candidate?", ru: "Что такое кандидат?", pl: "Czym jest kandydat?" },
        a: { en: "A candidate is a person you actively process toward hire: stages, documents, ownership, and next actions.", ru: "Кандидат — человек, с которым вы активно работаете до найма: этапы, документы, ответственность, следующие шаги.", pl: "Kandydat to osoba, którą aktywnie prowadzisz do zatrudnienia: etapy, dokumenty, ownership, kolejne kroki." },
      },
      {
        id: "what_order",
        q: { en: "What is an order?", ru: "Что такое заказ (order)?", pl: "Czym jest zamówienie (order)?" },
        a: { en: "A sales/service order is the commercial request from a client (positions to fill). Vacancies and billable work can hang off order lines when Sales is enabled.", ru: "Заказ — коммерческий запрос клиента (кого нанять). Вакансии и биллинг могут идти от строк заказа, если включён Sales.", pl: "Zamówienie to komercyjne żądanie klienta (kogo zatrudnić). Wakaty i billing mogą wynikać z linii zamówienia przy włączonym Sales." },
      },
      {
        id: "pipeline",
        q: { en: "How does the pipeline work?", ru: "Как работает pipeline?", pl: "Jak działa pipeline?" },
        a: { en: "Candidates move through stages with an owner and next action. Pipeline and lists show who is stuck so you can close vacancies faster.", ru: "Кандидаты идут по этапам с владельцем и следующим шагом. Пайплайн и списки показывают, кто застрял — чтобы быстрее закрывать вакансии.", pl: "Kandydaci idą przez etapy z właścicielem i kolejnym krokiem. Pipeline i listy pokazują, kto utknął — by szybciej zamykać wakaty." },
      },
    ],
  },
  {
    id: "documents",
    title: { en: "Documents", ru: "Документы", pl: "Dokumenty" },
    items: [
      {
        id: "how_docs",
        q: { en: "How do documents work?", ru: "Как работают документы?", pl: "Jak działają dokumenty?" },
        a: { en: "Required documents are attached to the hiring process. Candidates upload via portal/link; statuses show missing, received, approved, or expired.", ru: "Нужные документы привязаны к процессу найма. Кандидат загружает через портал/ссылку; статусы: нет, получен, одобрен, истёк.", pl: "Wymagane dokumenty są w procesie rekrutacji. Kandydat wgrywa przez portal/link; statusy: brak, otrzymany, zatwierdzony, wygasły." },
      },
      {
        id: "red_doc",
        q: { en: "Why is a document red?", ru: "Почему документ красный?", pl: "Dlaczego dokument jest czerwony?" },
        a: { en: "Red usually means missing, rejected, or expired — a blocker for the next stage. Open the candidate and fix or request the file.", ru: "Красный обычно значит отсутствует, отклонён или истёк — блокер следующего этапа. Откройте кандидата и исправьте / запросите файл.", pl: "Czerwony zwykle oznacza brak, odrzucenie lub wygaśnięcie — bloker kolejnego etapu. Otwórz kandydata i popraw / poproś o plik." },
      },
      {
        id: "expiry",
        q: { en: "What is document expiry?", ru: "Что такое срок действия документа?", pl: "Czym jest termin ważności dokumentu?" },
        a: { en: "Many permits and IDs have an end date. HostFlow tracks expiry so you can renew before deployment is blocked.", ru: "У многих разрешений и ID есть дата окончания. HostFlow следит за сроком, чтобы успеть обновить до блокировки выхода.", pl: "Wiele zezwoleń i ID ma datę końca. HostFlow śledzi ważność, by odnowić zanim wyjście zostanie zablokowane." },
      },
      {
        id: "portal_upload",
        q: { en: "Can candidates upload documents themselves?", ru: "Может ли кандидат сам загрузить документы?", pl: "Czy kandydat może sam wgrać dokumenty?" },
        a: { en: "Yes, via the candidate portal / personal link when portal features are on your plan.", ru: "Да, через портал кандидата / персональную ссылку, если портал есть в тарифе.", pl: "Tak, przez portal kandydata / osobisty link, jeśli portal jest w planie." },
      },
      {
        id: "doc_types",
        q: { en: "Where do document types come from?", ru: "Откуда берутся типы документов?", pl: "Skąd biorą się typy dokumentów?" },
        a: { en: "Shared platform reference types — not a private list per company. Requirements are configured on the process/vacancy.", ru: "Общие справочники платформы — не локальный список компании. Требования настраиваются на процессе/вакансии.", pl: "Wspólne typy platformy — nie lokalna lista firmy. Wymagania ustawia się na procesie/wakacie." },
      },
      {
        id: "doc_control",
        q: { en: "How do I see missing documents across the team?", ru: "Как увидеть недостающие документы по команде?", pl: "Jak zobaczyć braki dokumentów w zespole?" },
        a: { en: "Use candidate lists, dashboards, and reminders filtered by document readiness / expiry.", ru: "Списки кандидатов, дашборды и напоминания с фильтром по готовности / сроку документов.", pl: "Listy kandydatów, dashboardy i przypomnienia z filtrem gotowości / ważności dokumentów." },
      },
    ],
  },
  {
    id: "billing",
    title: { en: "Billing", ru: "Биллинг", pl: "Billing" },
    items: [
      {
        id: "how_pay",
        q: { en: "How do I pay?", ru: "Как оплатить?", pl: "Jak zapłacić?" },
        a: { en: "Open Billing in settings, choose a plan, and complete checkout when payment is enabled for your tenant. Enterprise is contact sales.", ru: "Billing в настройках — выберите тариф и checkout, когда оплата включена. Enterprise — через sales.", pl: "Billing w ustawieniach — wybierz plan i checkout, gdy płatność jest włączona. Enterprise — przez sales." },
      },
      {
        id: "change_plan",
        q: { en: "How do I change plan?", ru: "Как сменить тариф?", pl: "Jak zmienić plan?" },
        a: { en: "In Billing select another plan. Workspace data stays; limits and modules follow the new plan.", ru: "В Billing выберите другой тариф. Данные workspace сохраняются; лимиты и модули — по новому плану.", pl: "W Billing wybierz inny plan. Dane workspace zostają; limity i moduły — według nowego planu." },
      },
      {
        id: "invoice",
        q: { en: "How do I get an invoice?", ru: "Как получить счёт?", pl: "Jak dostać fakturę?" },
        a: { en: "Paid invoices appear in Billing / Invoices after checkout or from finance flows on Business+. Contact sales for Enterprise invoicing.", ru: "Оплаченные счета — в Billing / Invoices после checkout или в finance-потоках Business+. Enterprise — через sales.", pl: "Opłacone faktury — w Billing / Invoices po checkout lub w finance Business+. Enterprise — przez sales." },
      },
      {
        id: "after_trial",
        q: { en: "What happens after Trial?", ru: "Что будет после Trial?", pl: "Co po Trial?" },
        a: { en: "Trial uses reduced caps. When it ends, choose Solo / Team / Business or talk to sales for Enterprise. Data is kept; features follow the selected plan.", ru: "На Trial сниженные капы. После — Solo / Team / Business или Enterprise через sales. Данные сохраняются; функции — по тарифу.", pl: "Trial ma obniżone limity. Potem Solo / Team / Business albo Enterprise przez sales. Dane zostają; funkcje wg planu." },
      },
      {
        id: "limits",
        q: { en: "Where are plan limits listed?", ru: "Где смотреть лимиты тарифов?", pl: "Gdzie są limity planów?" },
        a: { en: "On the public Pricing page and in-product Billing. Seats, workspaces, leads/month, and vacancies are plan-specific.", ru: "На публичном Pricing и в Billing. Места, workspace, лиды/мес и вакансии зависят от тарифа.", pl: "Na publicznym Pricing i w Billing. Miejsca, workspace, leady/mies. i wakaty zależą od planu." },
      },
      {
        id: "cancel",
        q: { en: "Can I cancel?", ru: "Можно ли отменить подписку?", pl: "Czy mogę anulować subskrypcję?" },
        a: { en: "Manage or cancel from Billing when self-serve billing is active, or contact support/sales for assisted accounts.", ru: "Управление/отмена в Billing при self-serve, либо через support/sales для сопровождаемых аккаунтов.", pl: "Zarządzanie/anulowanie w Billing przy self-serve albo przez support/sales dla kont wspieranych." },
      },
    ],
  },
  {
    id: "security",
    title: { en: "Security & GDPR", ru: "Безопасность и GDPR", pl: "Bezpieczeństwo i GDPR" },
    items: [
      {
        id: "where_data",
        q: { en: "Where is data stored?", ru: "Где хранятся данные?", pl: "Gdzie są przechowywane dane?" },
        a: { en: "In HostFlow’s cloud database and object storage with tenant isolation (including row-level security). See Privacy / security docs for regions and processors.", ru: "В облачной БД и object storage HostFlow с изоляцией tenant (включая RLS). Регионы и процессоры — в Privacy / security docs.", pl: "W chmurowej DB i object storage HostFlow z izolacją tenanta (w tym RLS). Regiony i procesory — w Privacy / security docs." },
      },
      {
        id: "gdpr",
        q: { en: "How does GDPR work in HostFlow?", ru: "Как в HostFlow работает GDPR?", pl: "Jak działa GDPR w HostFlow?" },
        a: { en: "Tenant-scoped data, role-based access, audit trails, and lead/candidate communication policies (including art.14 notice flows where configured).", ru: "Данные в рамках tenant, RBAC, аудит и политики коммуникаций по лидам/кандидатам (включая art.14, если настроено).", pl: "Dane w tenantcie, RBAC, audyt i polityki komunikacji lead/kandydat (w tym art.14, jeśli skonfigurowane)." },
      },
      {
        id: "delete_data",
        q: { en: "Can I delete data?", ru: "Можно ли удалить данные?", pl: "Czy mogę usunąć dane?" },
        a: { en: "Yes — operators can delete or anonymize records per product flows; platform data-deletion requests follow the published data-deletion process.", ru: "Да — операторы удаляют/анонимизируют по продуктовым сценариям; запросы на уровне платформы — по опубликованному data-deletion процессу.", pl: "Tak — operatorzy usuwają/anonimizują wg scenariuszy produktu; żądania platformowe — wg opublikowanego procesu data-deletion." },
      },
      {
        id: "access",
        q: { en: "Who can see my candidates?", ru: "Кто видит моих кандидатов?", pl: "Kto widzi moich kandydatów?" },
        a: { en: "Only users in your tenant with the right roles/permissions. Client portal access is explicit and time-bound when used.", ru: "Только пользователи вашего tenant с нужными ролями. Клиентский портал — только при явной выдаче доступа и сроках.", pl: "Tylko użytkownicy Twojego tenanta z właściwymi rolami. Portal klienta — tylko przy jawnym dostępie i terminie." },
      },
      {
        id: "2fa",
        q: { en: "Is there SSO / 2FA?", ru: "Есть ли SSO / 2FA?", pl: "Czy jest SSO / 2FA?" },
        a: { en: "Enterprise plans cover SSO roadmap items. Check Billing/Enterprise with sales for current MFA/SSO options.", ru: "SSO — в контуре Enterprise. Актуальные MFA/SSO уточняйте в Billing/у sales.", pl: "SSO — w Enterprise. Aktualne MFA/SSO ustal z Billing/sales." },
      },
      {
        id: "breach",
        q: { en: "How are security incidents handled?", ru: "Как обрабатывают инциденты безопасности?", pl: "Jak obsługiwane są incydenty bezpieczeństwa?" },
        a: { en: "HostFlow follows its security operating model and incident response process documented in the security canon.", ru: "По security operating model и IR-процессу из security-канона HostFlow.", pl: "Według security operating model i procesu IR z kanonu security HostFlow." },
      },
    ],
  },
  {
    id: "api",
    title: { en: "API & integrations", ru: "API и интеграции", pl: "API i integracje" },
    items: [
      {
        id: "has_api",
        q: { en: "Is there an API?", ru: "Есть ли API?", pl: "Czy jest API?" },
        a: { en: "Yes — HostFlow exposes authenticated REST APIs under /api/v1 for CRM operations. Access requires a tenant token and proper roles.", ru: "Да — REST API под /api/v1 для CRM. Нужен токен tenant и роли.", pl: "Tak — REST API pod /api/v1 dla CRM. Potrzebny token tenanta i role." },
      },
      {
        id: "webhooks",
        q: { en: "Do you support webhooks?", ru: "Есть ли webhook?", pl: "Czy są webhooki?" },
        a: { en: "Inbound lead webhooks and integration installs are available on eligible plans (Team+ for generic JSON inbound).", ru: "Входящие webhook лидов и установки интеграций — на подходящих тарифах (generic JSON inbound с Team+).", pl: "Przychodzące webhooki leadów i instalacje integracji — na planach uprawnionych (generic JSON inbound od Team+)." },
      },
      {
        id: "oauth",
        q: { en: "Is OAuth supported?", ru: "Поддерживается ли OAuth?", pl: "Czy jest OAuth?" },
        a: { en: "Meta and other providers use OAuth where the integration supports it. App credentials are configured by HostFlow / tenant admin.", ru: "Meta и другие провайдеры — через OAuth, где интеграция это поддерживает. Credentials настраивает HostFlow / admin tenant.", pl: "Meta i inni dostawcy — przez OAuth, gdzie integracja to wspiera. Credentials ustawia HostFlow / admin tenanta." },
      },
      {
        id: "rate_limits",
        q: { en: "Are there API rate limits?", ru: "Есть ли rate limit у API?", pl: "Czy API ma rate limit?" },
        a: { en: "Yes — platform and plan fair-use limits apply. Prefer webhooks for high-volume inbound instead of polling.", ru: "Да — лимиты платформы и fair-use тарифа. Для большого inbound лучше webhook, а не polling.", pl: "Tak — limity platformy i fair-use planu. Przy dużym inbound lepiej webhook niż polling." },
      },
      {
        id: "ext_crm",
        q: { en: "Can I sync with another CRM?", ru: "Можно ли синхронизировать с другой CRM?", pl: "Czy mogę synchronizować z innym CRM?" },
        a: { en: "Via API/webhooks or Marketplace integrations when available. Custom sync is an Enterprise/services discussion.", ru: "Через API/webhook или Marketplace-интеграции. Кастомный sync — с Enterprise/services.", pl: "Przez API/webhook lub integracje Marketplace. Custom sync — rozmowa Enterprise/services." },
      },
      {
        id: "docs_api",
        q: { en: "Where is API documentation?", ru: "Где документация API?", pl: "Gdzie jest dokumentacja API?" },
        a: { en: "Use the in-product developer notes and OpenAPI/schema exports for your deployment. Contact support if your tenant needs a documented integration package.", ru: "In-product developer notes и OpenAPI/схемы деплоя. Нужен пакет интеграции — напишите в support.", pl: "In-product developer notes i OpenAPI/schematy deploymentu. Potrzebny pakiet integracji — napisz do support." },
      },
    ],
  },
]

export function faqLocaleFromApp(locale: string | undefined): FaqLocale {
  if (!locale) return 'en'
  if (locale.startsWith('ru')) return 'ru'
  if (locale.startsWith('pl')) return 'pl'
  return 'en'
}

export function flattenFaqItems(sections: FaqSection[] = FAQ_SECTIONS) {
  return sections.flatMap((section) =>
    section.items.map((item) => ({ ...item, sectionId: section.id, sectionTitle: section.title })),
  )
}

