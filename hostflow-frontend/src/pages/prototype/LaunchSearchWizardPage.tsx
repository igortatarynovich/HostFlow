import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconArrowRight } from '@tabler/icons-react'
import { LaunchSearchFlowChrome } from '../../components/prototype/LaunchSearchFlowChrome'
import {
  LaunchSearchLeadCard,
  LaunchSearchReadyAssets,
} from '../../components/prototype/LaunchSearchLeadCard'
import { savePrototypeSearch, type PrototypeSearch } from './launchSearchPrototype'

const MOCK_CLIENTS = ['Poltrakt', 'Amazon Logistics', 'Focus Personnel'] as const

const TOTAL_STEPS = 7

type WizardStep = 1 | 2 | 3 | 4 | 5 | 6 | 7

type RoleChoice = 'driver_ce' | 'warehouse' | 'office' | 'company' | 'other' | ''
type LicenseChoice = 'ce' | 'c' | 'ce_no_e' | ''
type ChannelState = { meta: boolean; link: boolean; qr: boolean }
type AssigneeChoice = 'self' | 'colleague' | 'auto' | ''

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

function OptionCard({
  selected,
  onClick,
  children,
  disabled,
  soon,
  testId,
}: {
  selected: boolean
  onClick: () => void
  children: React.ReactNode
  disabled?: boolean
  soon?: boolean
  testId?: string
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      disabled={disabled}
      data-testid={testId}
      onClick={onClick}
      className={`rounded-xl border-2 p-4 text-left text-sm transition ${
        disabled
          ? 'cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400'
          : selected
            ? 'border-brand-400 bg-brand-50/80 ring-2 ring-brand-200'
            : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span>{children}</span>
        {soon ? (
          <span className="shrink-0 rounded-lg bg-slate-100 px-2 py-0.5 text-xs text-slate-500">Скоро</span>
        ) : null}
      </div>
    </button>
  )
}

function NavButtons({
  onBack,
  onNext,
  nextLabel = 'Далее',
  nextDisabled,
  showBack = true,
}: {
  onBack?: () => void
  onNext: () => void
  nextLabel?: string
  nextDisabled?: boolean
  showBack?: boolean
}) {
  return (
    <div className="mt-6 flex flex-wrap justify-between gap-3">
      {showBack && onBack ? (
        <button
          type="button"
          onClick={onBack}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Назад
        </button>
      ) : (
        <span />
      )}
      <button
        type="button"
        onClick={onNext}
        disabled={nextDisabled}
        className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {nextLabel}
        <IconArrowRight size={16} />
      </button>
    </div>
  )
}

export default function LaunchSearchWizardPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<WizardStep>(1)
  const [showLeadPreview, setShowLeadPreview] = useState(false)

  const [role, setRole] = useState<RoleChoice>('driver_ce')
  const [forClient, setForClient] = useState<'client' | 'own' | ''>('client')
  const [clientName, setClientName] = useState<string>(MOCK_CLIENTS[0])
  const [newClientName, setNewClientName] = useState('')
  const [addingClient, setAddingClient] = useState(false)
  const [license, setLicense] = useState<LicenseChoice>('ce')
  const [searchName, setSearchName] = useState('')
  const [channels, setChannels] = useState<ChannelState>({ meta: true, link: true, qr: false })
  const [metaConnected, setMetaConnected] = useState(true)
  const [assignee, setAssignee] = useState<AssigneeChoice>('self')

  const effectiveClient = addingClient ? newClientName.trim() : clientName

  const suggestedName = useMemo(() => {
    if (!effectiveClient) return 'Водители C+E'
    return `Водители C+E — ${effectiveClient}`
  }, [effectiveClient])

  const displayName = searchName.trim() || suggestedName

  const formUrl = useMemo(() => {
    const slug = slugify(effectiveClient || 'client')
    return `https://forms.hostflow.app/${slug}-voditeli-ce`
  }, [effectiveClient])

  const channelLabels = useMemo(() => {
    const labels: string[] = []
    if (channels.meta) labels.push('Meta')
    if (channels.link) labels.push('Ссылка')
    if (channels.qr) labels.push('QR')
    return labels
  }, [channels])

  function goNext() {
    if (step < TOTAL_STEPS) setStep((s) => (s + 1) as WizardStep)
  }

  function goBack() {
    if (step > 1) setStep((s) => (s - 1) as WizardStep)
  }

  function finish() {
    const search: PrototypeSearch = {
      id: crypto.randomUUID(),
      name: displayName,
      clientName: effectiveClient,
      licenseType: license === 'ce' ? 'C+E' : license === 'c' ? 'C' : 'CE',
      channels: channelLabels,
      assignee: assignee === 'self' ? 'Я' : assignee === 'auto' ? 'Автоматически' : 'Коллега',
      formUrl,
      createdAt: new Date().toISOString(),
      stats: { leads: 0, candidates: 0, interviews: 0 },
    }
    savePrototypeSearch(search)
    navigate('/app/recruitment/searches')
  }

  const stepMeta: Record<WizardStep, { title: string; subtitle?: string }> = {
    1: {
      title: 'Кого хотите найти?',
      subtitle: 'Выберите тип людей, которых хотите привлечь через рекламу или анкету.',
    },
    2: {
      title: 'Для кого ищете?',
      subtitle: 'Укажите, для какой компании вы запускаете поиск.',
    },
    3: {
      title: 'Какие права нужны?',
      subtitle: 'Это поможет собрать правильную анкету для водителей.',
    },
    4: {
      title: 'Как назвать этот поиск?',
      subtitle: 'Название поможет отличать поиски на главном экране.',
    },
    5: {
      title: 'Как будете получать заявки?',
      subtitle: 'Можно выбрать несколько способов сразу.',
    },
    6: {
      title: 'Кто будет обрабатывать заявки?',
      subtitle: 'Новые заявки будут попадать к этому человеку.',
    },
    7: {
      title: 'Всё готово',
      subtitle: 'Можете запускать рекламу или делиться ссылкой на анкету.',
    },
  }

  const { title, subtitle } = stepMeta[step]

  return (
    <LaunchSearchFlowChrome step={step} totalSteps={TOTAL_STEPS} title={title} subtitle={subtitle}>
      {step === 1 ? (
        <div className="space-y-4">
          <div className="grid gap-3" role="radiogroup" aria-label="Тип поиска">
            <OptionCard
              selected={role === 'driver_ce'}
              onClick={() => setRole('driver_ce')}
              testId="launch-search-role-driver"
            >
              Водитель (C+E)
            </OptionCard>
            <OptionCard selected={false} onClick={() => {}} disabled soon>
              Работник склада
            </OptionCard>
            <OptionCard selected={false} onClick={() => {}} disabled soon>
              Офисный сотрудник
            </OptionCard>
            <OptionCard selected={false} onClick={() => {}} disabled soon>
              Компания-клиент
            </OptionCard>
            <OptionCard selected={false} onClick={() => {}} disabled soon>
              Другое
            </OptionCard>
          </div>
          <NavButtons onNext={goNext} showBack={false} />
        </div>
      ) : null}

      {step === 2 ? (
        <div className="space-y-4">
          <div className="grid gap-3" role="radiogroup" aria-label="Для кого">
            <OptionCard
              selected={forClient === 'client'}
              onClick={() => {
                setForClient('client')
                setAddingClient(false)
              }}
              testId="launch-search-for-client"
            >
              Для клиента
            </OptionCard>
            <OptionCard
              selected={forClient === 'own'}
              onClick={() => setForClient('own')}
              testId="launch-search-for-own"
            >
              Для своей компании
            </OptionCard>
          </div>

          {forClient === 'client' ? (
            <div className="space-y-3 pt-2">
              <p className="text-sm font-medium text-slate-700">Выберите клиента</p>
              <div className="grid gap-2" role="radiogroup">
                {MOCK_CLIENTS.map((client) => (
                  <OptionCard
                    key={client}
                    selected={!addingClient && clientName === client}
                    onClick={() => {
                      setAddingClient(false)
                      setClientName(client)
                    }}
                  >
                    {client}
                  </OptionCard>
                ))}
                <OptionCard
                  selected={addingClient}
                  onClick={() => setAddingClient(true)}
                  testId="launch-search-add-client"
                >
                  + Добавить нового клиента
                </OptionCard>
              </div>
              {addingClient ? (
                <input
                  type="text"
                  value={newClientName}
                  onChange={(e) => setNewClientName(e.target.value)}
                  placeholder="Название компании"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  data-testid="launch-search-new-client-input"
                />
              ) : null}
            </div>
          ) : null}

          <NavButtons
            onBack={goBack}
            onNext={goNext}
            nextDisabled={
              forClient === '' ||
              (forClient === 'client' && !effectiveClient)
            }
          />
        </div>
      ) : null}

      {step === 3 ? (
        <div className="space-y-4">
          <div className="grid gap-3" role="radiogroup" aria-label="Права">
            <OptionCard selected={license === 'ce'} onClick={() => setLicense('ce')}>
              C+E (международные перевозки)
            </OptionCard>
            <OptionCard selected={license === 'c'} onClick={() => setLicense('c')}>
              C (только категория C)
            </OptionCard>
            <OptionCard selected={license === 'ce_no_e'} onClick={() => setLicense('ce_no_e')}>
              CE без E
            </OptionCard>
          </div>
          <NavButtons onBack={goBack} onNext={goNext} nextDisabled={!license} />
        </div>
      ) : null}

      {step === 4 ? (
        <div className="space-y-4">
          <label className="block text-sm font-medium text-slate-700" htmlFor="search-name">
            Название поиска
          </label>
          <input
            id="search-name"
            type="text"
            value={searchName}
            onChange={(e) => setSearchName(e.target.value)}
            placeholder={suggestedName}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            data-testid="launch-search-name-input"
          />
          <p className="text-xs text-slate-500">
            Если оставить пустым, будет использовано: «{suggestedName}»
          </p>
          <NavButtons onBack={goBack} onNext={goNext} />
        </div>
      ) : null}

      {step === 5 ? (
        <div className="space-y-4">
          <div className="space-y-3">
            <label className="flex items-center gap-3 rounded-xl border border-slate-200 p-4 text-sm">
              <input
                type="checkbox"
                checked={channels.meta}
                onChange={(e) => setChannels((c) => ({ ...c, meta: e.target.checked }))}
                className="h-4 w-4 rounded border-slate-300 text-brand-600"
              />
              <span>
                <span className="font-medium text-slate-900">Meta</span>
                <span className="mt-0.5 block text-slate-600">Facebook / Instagram реклама</span>
              </span>
            </label>
            <label className="flex items-center gap-3 rounded-xl border border-slate-200 p-4 text-sm">
              <input
                type="checkbox"
                checked={channels.link}
                onChange={(e) => setChannels((c) => ({ ...c, link: e.target.checked }))}
                className="h-4 w-4 rounded border-slate-300 text-brand-600"
              />
              <span>
                <span className="font-medium text-slate-900">Ссылка на анкету</span>
                <span className="mt-0.5 block text-slate-600">Отправить кандидатам или разместить на сайте</span>
              </span>
            </label>
            <label className="flex items-center gap-3 rounded-xl border border-slate-200 p-4 text-sm">
              <input
                type="checkbox"
                checked={channels.qr}
                onChange={(e) => setChannels((c) => ({ ...c, qr: e.target.checked }))}
                className="h-4 w-4 rounded border-slate-300 text-brand-600"
              />
              <span>
                <span className="font-medium text-slate-900">QR-код</span>
                <span className="mt-0.5 block text-slate-600">Для печати на визитках, плакатах, офисе</span>
              </span>
            </label>
          </div>

          {channels.meta && !metaConnected ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm">
              <p className="text-amber-900">Meta ещё не подключена.</p>
              <button
                type="button"
                className="mt-2 font-medium text-brand-700 hover:underline"
                onClick={() => setMetaConnected(true)}
              >
                Подключить Meta сейчас
              </button>
            </div>
          ) : null}

          <NavButtons
            onBack={goBack}
            onNext={goNext}
            nextDisabled={!channels.meta && !channels.link && !channels.qr}
          />
        </div>
      ) : null}

      {step === 6 ? (
        <div className="space-y-4">
          <div className="grid gap-3" role="radiogroup" aria-label="Ответственный">
            <OptionCard selected={assignee === 'self'} onClick={() => setAssignee('self')}>
              Я сам
            </OptionCard>
            <OptionCard selected={assignee === 'colleague'} onClick={() => setAssignee('colleague')}>
              Выбрать сотрудника
            </OptionCard>
            <OptionCard selected={assignee === 'auto'} onClick={() => setAssignee('auto')}>
              Распределять автоматически
            </OptionCard>
          </div>
          <NavButtons
            onBack={goBack}
            onNext={goNext}
            nextLabel="Готово"
            nextDisabled={!assignee}
          />
        </div>
      ) : null}

      {step === 7 ? (
        <div className="space-y-6">
          <LaunchSearchReadyAssets
            searchName={displayName}
            formUrl={formUrl}
            channels={channels}
            metaConnected={metaConnected}
          />

          {showLeadPreview ? (
            <LaunchSearchLeadCard searchName={displayName} clientName={effectiveClient} />
          ) : (
            <button
              type="button"
              onClick={() => setShowLeadPreview(true)}
              className="w-full rounded-xl border border-dashed border-slate-300 px-4 py-3 text-sm font-medium text-slate-700 hover:border-brand-300 hover:bg-brand-50/30"
              data-testid="launch-search-preview-lead"
            >
              Посмотреть, как будет выглядеть первая заявка
            </button>
          )}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={finish}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              data-testid="launch-search-finish"
            >
              Перейти к поиску
            </button>
            <Link
              to="/app/recruitment/searches/new"
              onClick={() => {
                setStep(1)
                setShowLeadPreview(false)
                setSearchName('')
              }}
              className="inline-flex items-center justify-center rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Запустить ещё один
            </Link>
          </div>
        </div>
      ) : null}
    </LaunchSearchFlowChrome>
  )
}
