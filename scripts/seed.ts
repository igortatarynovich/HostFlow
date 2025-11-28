// scripts/seed.ts
/* eslint-disable no-console */
import axios from 'axios'

// === CONFIG ===
const BASE = process.env.HF_API_BASE || process.env.API_BASE || 'http://127.0.0.1:8000/api/v1'
const RAW_TOKEN = process.env.HF_API_TOKEN || process.env.API_TOKEN || '' // bare JWT is expected
const TENANT = process.env.HF_TENANT_ID || process.env.TENANT_ID || ''
const TOTAL_COMPANIES = 5
const TOTAL_VACANCIES = 7
const TOTAL_CANDIDATES = 70

let DISABLE_DOC_POST = false
let DOC_POST_FAILS = 0
const MAX_DOC_FAILS = 8
let DOCS_CREATED = 0

// === HTTP helper ===
const http = axios.create({
  baseURL: BASE,
  headers: {
    ...(RAW_TOKEN ? { Authorization: `Bearer ${RAW_TOKEN}` } : {}),
    ...(TENANT ? { 'X-Tenant-Id': TENANT } : {}),
    'Content-Type': 'application/json',
  },
  timeout: 15000,
})

async function safe<T>(p: Promise<{ data: T }>, label: string): Promise<T | null> {
  try {
    const { data } = await p
    return data as T
  } catch (e: any) {
    const status = e?.response?.status
    const payload = e?.response?.data
    const msg = (payload?.detail || payload?.message || e?.message || 'Error')
    const pretty = payload ? `\n${JSON.stringify(payload, null, 2)}` : ''
    console.warn(`[skip] ${label}${status ? ` [${status}]` : ''}: ${msg}${pretty}`)
    return null
  }
}

function rand<T>(arr: T[]): T { return arr[Math.floor(Math.random() * arr.length)] }
function chance(p: number) { return Math.random() < p }
function randint(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min }
function pickN<T>(arr: T[], n: number): T[] {
  const c = [...arr]; const out: T[] = []
  while (out.length < n && c.length) out.push(c.splice(Math.floor(Math.random()*c.length),1)[0])
  return out
}

// === reference ===
const COUNTRIES = ['PL','LT','LV','EE','DE','CZ','SK','RO','BG','HU','AT','NL','BE','ES','PT','IT','FI','SE','NO','DK','IE','GB','AE','TR','UA','KZ','UZ','AM','GE']
const LANGS = ['en','pl','lt','lv','ru','uk','de','cz','sk','ro','bg','hu','nl','es','pt','it','fi','sv','no','da','tr','ar']
const STAGE_FALLBACK = ['new','interview','hiring','employed','probation','rejected']

const companyNames = [
  'Nordex Logistics', 'BalticCrew', 'EuroManpower', 'HostFlow Demo GmbH', 'Maritime Partners',
  'CargoWay', 'Polar Star Ops', 'TransDock Solutions', 'Aquila Services', 'Harborline'
]
const cities = ['Warsaw','Vilnius','Riga','Tallinn','Gdansk','Gdynia','Hamburg','Rotterdam','Antwerp','Lisbon','Porto','Valencia','Naples','Genoa','Athens','Oslo','Helsinki','Copenhagen']
const positions = [
  'Loader', 'Forklift Operator', 'Warehouse Picker', 'Sailor', 'Deckhand',
  'Mechanic', 'Electrician', 'Driver', 'Dispatcher', 'Cook', 'Waiter', 'Cleaning Specialist'
]

// === shared: load meta ===
async function getStages(): Promise<string[]> {
  const data = await safe<any>(http.get('/meta/stages'), 'GET /meta/stages')
  if (Array.isArray(data)) {
    const codes = data.map((x: any)=> typeof x==='string'? x : x?.code).filter(Boolean)
    return codes.length ? codes : STAGE_FALLBACK
  }
  return STAGE_FALLBACK
}

type Manager = { id: string; name?: string; email?: string }
async function getManagers(): Promise<Manager[]> {
  const data = await safe<any>(http.get('/catalogs/managers'), 'GET /catalogs/managers')
  const list = Array.isArray(data) ? data : data?.items || []
  return list.map((m: any)=>({ id: m.id || m.user_id || m.uid, name: m.name, email: m.email })).filter((m:any)=>m.id)
}

// === create helpers ===
async function createCompany(payload: any) {
  const created = await safe<any>(http.post('/companies/', payload), 'POST /companies/')
  if (created) return created
  return await safe<any>(http.post('/companies', payload), 'POST /companies')
}

async function createVacancy(payload: any) {
  // бек иногда использует /vacancies/ со слэшем — поддержим оба
  const created = await safe<any>(http.post('/vacancies', payload), 'POST /vacancies')
  if (created) return created
  return await safe<any>(http.post('/vacancies/', payload), 'POST /vacancies/')
}

async function createCandidate(payload: any) {
  return await safe<any>(http.post('/candidates', payload), 'POST /candidates')
}

async function createCandidateDocument(candidateId: string, base: any) {
  if (DISABLE_DOC_POST) return null

  // Always send the minimal, explicit shape that backend requires
  const key = base.key || base.code || base.document_type || base.type || base.doc_type
  const payload: any = {
    key,
    title: base.title,
    number: base.number,
    issued_at: base.issued_at,
    expires_at: base.expires_at,
    note: base.note,
    status: base.status || 'planned',
  }
  // strip undefined/null
  Object.keys(payload).forEach((k)=> (payload[k] === undefined || payload[k] === null) && delete payload[k])

  try {
    const { data } = await http.post(`/candidates/${candidateId}/documents`, payload)
    return data
  } catch (e: any) {
    const status = e?.response?.status
    const detail = e?.response?.data?.detail || e?.message || ''

    // If server errors occur repeatedly, stop posting docs to avoid log spam.
    if (status === 500) {
      DOC_POST_FAILS += 1
      console.warn(`[warn] candidate-doc POST 500 (fail #${DOC_POST_FAILS}). Will continue up to ${MAX_DOC_FAILS} fails before disabling.`)
      if (DOC_POST_FAILS >= MAX_DOC_FAILS) {
        console.warn('[skip] documents API disabled for this run due to repeated 500s.')
        DISABLE_DOC_POST = true
      }
      return null
    }

    // FastAPI validation requires `key`
    if (status === 422) {
      console.warn(`[skip] POST /candidates/${candidateId}/documents [422]: validation failed. Payload sent: ${JSON.stringify(payload)}`)
      return null
    }

    console.warn(`[skip] POST /candidates/${candidateId}/documents${status ? ` [${status}]` : ''}: ${detail || 'Error'}`)
    return null
  }
}

async function getDocumentTypes(): Promise<any[]> {
  // For now, don’t rely on backend routes which may differ across branches.
  // Use a stable, static set so seeding always works.
  return [
    { code: 'passport', name: 'Passport', required: true },
    { code: 'photo', name: 'Photo', required: true },
    { code: 'license', name: 'License', required: false },
    { code: 'contract', name: 'Employment Contract', required: false },
  ]
}

// === generators ===
function phoneMeta(country: string) {
  const code =
    country === 'PL' ? '+48' :
    country === 'LT' ? '+370' :
    country === 'LV' ? '+371' :
    country === 'EE' ? '+372' :
    country === 'DE' ? '+49' : '+44'
  // national number without country code
  const national = `${randint(500,999)}${randint(100,999)}${randint(100,999)}`
  return { code, national }
}

function makeName(i: number) {
  const first = ['Ivan','Pavel','Oleh','Dmitry','Ali','Lukas','Jonas','Marek','Piotr','Andrii','Sven','Erik','Marco','Luis','Tiago','Artur','Rashid','Said','Denis','Nikita']
  const last = ['Kowalski','Novak','Ivanov','Petrov','Shevchenko','Nowak','Muller','Schmidt','Kovalenko','Jankowski','Kuznetsov','Ortega','Marquez','Popov','Sokolov','Bianchi','Rossi','Khalil','Ibrahim','Ferreira']
  return { first: rand(first), last: rand(last) }
}

function makeEmail(first: string, last: string, i:number) {
  const domains = ['mail.com','gmail.com','yahoo.com','outlook.com','proton.me','company.eu','demo.pl']
  return `${first}.${last}.${i}@${rand(domains)}`.toLowerCase()
}

function makeExtra(country: string, phone_code: string) {
  return {
    phone_country: country,
    phone_prefix: phone_code, // keep existing field name for UI compatibility
    address: { country, city: rand(cities), street: `Street ${randint(1,200)}`, house: String(randint(1,120)), apt: String(randint(1,50)), zip: `${randint(10,99)}-${randint(100,999)}` },
    reg_address_diff: chance(0.3),
    reg_address: { country, city: rand(cities), street: `Ave ${randint(1,200)}`, house: String(randint(1,120)), apt: String(randint(1,50)), zip: `${randint(10,99)}-${randint(100,999)}` },
    birth_date: `${randint(1975, 2002)}-${String(randint(1,12)).padStart(2,'0')}-${String(randint(1,28)).padStart(2,'0')}`,
    citizenship: rand(COUNTRIES),
    license_number: chance(0.6) ? `LIC-${randint(100000,999999)}` : '',
    license_categories: chance(0.5) ? pickN(['A','B','C','CE','D'], randint(1,3)) : [],
    previous_employers: pickN(companyNames, randint(0,3)),
    documents: {},
  }
}

type Company = { id: string; name: string }
type Vacancy = { id: string; title: string; company_id: string }

async function seed() {
  console.log(`Seeding to ${BASE} ...`)

  const stages = await getStages()
  console.log('Using stages:', stages.join(', '))

  const managers = await getManagers()
  if (!managers.length) {
    console.log('No managers from /catalogs/managers — candidates will be created without manager.')
  } else {
    console.log(`Managers available: ${managers.length}`)
  }

  // 1) Companies
  const companies: Company[] = []
  while (companies.length < TOTAL_COMPANIES) {
    const name = companyNames[companies.length % companyNames.length] + (companies.length > 4 ? ` ${companies.length}` : '')
    const payload = {
      name,
      country: rand(COUNTRIES),
      city: rand(cities),
      address: `HQ ${randint(10,200)}`,
      extra: { industry: 'Logistics', website: `https://www.${name.toLowerCase().replace(/\s+/g,'-')}.com` },
    }
    const created = await createCompany(payload)
    if (created?.id) {
      companies.push({ id: created.id, name })
      console.log('[company]', name)
    } else {
      // если нет эндпоинта — выходим из попыток, чтобы не застревать
      break
    }
  }
  // если компаниям отказали, создадим фиктивные id для линковки вакансий/кандидатов
  if (!companies.length) {
    for (let i=0;i<TOTAL_COMPANIES;i++) companies.push({ id: `cmp-${i+1}`, name: companyNames[i] || `Company ${i+1}` })
    console.log(`Companies mocked: ${companies.length}`)
  }

  // 2) Vacancies
  const vacancies: Vacancy[] = []
  for (let i=0;i<TOTAL_VACANCIES;i++) {
    const title = `${rand(positions)} — ${rand(['Day Shift','Night Shift','Rotational','Seasonal'])}`
    const company = rand(companies)
    const payload = {
      title,
      company_id: company.id,
      location: `${rand(cities)}, ${rand(COUNTRIES)}`,
      description: `Responsibilities: ${rand(['Loading/unloading','Warehouse operations','On-deck assistance','Basic maintenance'])}. Requirements: ${rand(['Experience 1+ year','Basic English','Work permit','Medical certificate'])}.`,
      salary_from: randint(800,1400),
      salary_to: randint(1500,2500),
      currency: rand(['EUR','PLN','USD']),
      employment_type: rand(['full_time','contract','seasonal']),
      // любые дополнительные
      extra: { shift: rand(['day','night','mixed']), housing: chance(0.5), meals: chance(0.4) },
    }
    const created = await createVacancy(payload)
    const id = created?.id || created?.vacancy_id || created?.data?.id
    if (id) {
      vacancies.push({ id, title, company_id: company.id })
      console.log('[vacancy]', title)
    } else {
      // если нет эндпоинта — создаём фиктивно
      const fake = { id: `v-${i+1}`, title, company_id: company.id }
      vacancies.push(fake)
      console.log('[vacancy:FALLBACK]', title)
    }
  }

  // 3) Document types (для генерации документов кандидатов)
  const docTypes = await getDocumentTypes()
  const codeToId = Object.fromEntries((docTypes || []).map((t:any)=> [t.code, t.id].filter(Boolean)).filter((x:any)=> x.length === 2))
  const requiredTypes = docTypes.filter((t:any)=> t.required).map((t:any)=> t.code)
  const optionalTypes = docTypes.filter((t:any)=> !t.required).map((t:any)=> t.code)

  // 4) Candidates
  let createdCount = 0
  for (let i=1;i<=TOTAL_CANDIDATES;i++) {
    const { first, last } = makeName(i)
    const fullName = `${first} ${last}`
    const email = makeEmail(first,last,i)
    const country = rand(COUNTRIES)
    const { code: phone_code, national: phone } = phoneMeta(country)
    const languages = pickN(LANGS, randint(1,3))
    const company = rand(companies)
    const vacancy = rand(vacancies)
    const manager = managers.length ? rand(managers).id : undefined
    const stage = rand(stages)

    const extra = makeExtra(country, phone_code)
    const docs_progress = {} // можно заполнить из созданных ниже документов

    const payload: any = {
      first_name: first,
      last_name: last,
      email,
      phone,                 // national number only, **without** country code
      phone_country: country,
      phone_code,            // if backend ignores it, it's fine; UI can read it from extra
      languages,
      stage,
      vacancy_id: vacancy.id,
      company_id: company.id,
      manager,
      note: chance(0.4) ? `Note: ${rand(['referred by friend','ex-employee','needs accommodation','available next week'])}` : undefined,
      extra: { ...extra, phone_country: country, phone_code },
      docs_progress,
    }

    const created = await createCandidate(payload)
    const candId: string = created?.id || created?.candidate_id || created?.data?.id
    if (!candId) {
      // если нет эндпоинта — пропускаем документы и идём дальше
      console.log('[candidate:FALLBACK]', fullName)
      continue
    }
    createdCount++
    console.log(`[candidate] ${i}/${TOTAL_CANDIDATES} ${fullName} (${stage})`)

    // 3–6 документов: все обязательные + часть необязательных
    // NOTE: posts are skipped if backend migrations for candidate documents aren’t applied (missing `candidate_id` column)
    const docCodes = [
      ...requiredTypes,
      ...pickN(optionalTypes, randint(0, 3))
    ]

    for (const code of docCodes) {
      const title = code === 'passport' ? `Passport ${last}` :
                    code === 'photo' ? `Photo ${first}` :
                    code === 'license' ? `License ${first} ${last}` :
                    code

      // CandDocCreate fields
      let number: string | undefined
      let issued_at: string | undefined
      let expires_at: string | undefined
      if (code === 'passport') {
        number = `P${randint(1000000,9999999)}`
        issued_at = `${randint(2015,2023)}-${String(randint(1,12)).padStart(2,'0')}-${String(randint(1,28)).padStart(2,'0')}`
        expires_at = `${randint(2026,2033)}-${String(randint(1,12)).padStart(2,'0')}-${String(randint(1,28)).padStart(2,'0')}`
      } else if (code === 'license') {
        number = `LIC-${randint(100000,999999)}`
        issued_at = `${randint(2016,2024)}-${String(randint(1,12)).padStart(2,'0')}-${String(randint(1,28)).padStart(2,'0')}`
      }

      const createdDoc = await createCandidateDocument(candId, {
        key: code,                       // e.g., passport/photo/license/contract
        type_id: codeToId[code],         // if backend expects an id variant
        document_type_id: codeToId[code],
        title,
        number,
        issued_at,
        expires_at,
        note: chance(0.2) ? rand(['scan ok','needs better quality','re-upload requested']) : undefined,
      })
      // count successes
      if (createdDoc && createdDoc.id) {
        DOCS_CREATED += 1
      }
      if (createdDoc) {
        (docs_progress as any)[code] = 'uploaded'
      } else if (DISABLE_DOC_POST) {
        // mark as planned locally so UI can still show placeholders
        (docs_progress as any)[code] = 'planned'
      }
    }
  }

  console.log('---')
  console.log(`Companies: ${companies.length}`)
  console.log(`Vacancies: ${vacancies.length}`)
  console.log(`Candidates created: ${createdCount}/${TOTAL_CANDIDATES}`)
  console.log(`Candidate documents created: ${DOCS_CREATED}`)
  console.log('Done.')
}

// run
seed().catch((e)=>{ console.error(e); process.exit(1) })