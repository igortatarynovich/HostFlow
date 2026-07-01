import { isAxiosError } from 'axios'
import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { Modal } from '../../components/Modal'
import { settings as tenantSettings, setToken } from '../../api/client'
import {
  changePlatformTenantStatus,
  createPlatformTenant,
  createTenantAdmin,
  decidePlatformSeatRequest,
  getPlatformTenantModules,
  getPlatformTenantLegalHostSettings,
  getPlatformTenantRoleModuleMatrix,
  getPlatformTenantUserModuleOverrides,
  impersonatePlatformTenant,
  listPlatformTenantModuleOverrideUsers,
  listPlatformTenants,
  listPlatformSeatRequests,
  listTenantVacancyAccess,
  listTenantVacancyOptions,
  updatePlatformTenantLicense,
  updatePlatformTenantMetadata,
  updatePlatformTenantModules,
  updatePlatformTenantLegalHostSettings,
  updatePlatformTenantRoleModuleMatrix,
  updatePlatformTenantUserModuleOverrides,
  updateTenantVacancyAccess,
  uploadPlatformTenantLogo,
  enrollPlatformTenantFounderPricing,
} from '../../api/tenants'
import type {
  PlatformTenant,
  PlatformTenantCreatePayload,
  SeatRequest,
  TenantLicense,
  TenantLicenseInput,
  TenantLicensePatchInput,
  TenantModuleSettings,
  TenantModuleSettingsPatch,
  TenantRoleModuleMatrix,
  TenantUserModuleOverrides,
  TenantModuleOverrideUser,
  RoleModuleMatrixRole,
  TenantStatus,
  TenantType,
  TenantLegalHostSettings,
  TenantVacancyAccessItem,
  TenantVacancyOption,
} from '../../api/types'
import { useAuth } from '../../store/useAuth'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'
import { STATUS_BADGE, TYPE_BADGE, MODULE_LABELS, SEAT_STATUS_BADGE } from '../../modules/tenants/constants'
import type { StatusFilter, TypeFilter, CreateTenantForm } from '../../modules/tenants/types'
import {
  DEFAULT_LICENSE,
  toLicenseForm,
  parseNumber,
  licenseFormToPatch,
  licenseFormToInput,
  formatValues,
  formatErrorMessage,
  type LicenseFormState,
} from '../../modules/tenants/utils'
import { SeatProgress } from '../../modules/tenants/components/SeatProgress'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'

const DEFAULT_CREATE_FORM: CreateTenantForm = {
  name: '',
  slug: '',
  workspace_label: '',
  type: 'agency',
  status: 'active',
  client_portal_enabled: true,
  status_sharing_allowed: false,
  license: {
    ...DEFAULT_LICENSE,
    plan: 'agency_basic',
    max_recruiters: '10',
    max_supervisors: '3',
    max_client_managers: '2',
    max_viewers: '5',
    max_storage_gb: '5',
    max_companies: '10',
  },
  initial_admin_email: '',
  initial_admin_name: '',
  initial_admin_password: '',
}

export default function TenantsPage() {
  const { t } = useI18n()
  const { me, refresh: refreshSession, beginImpersonation } = useAuth()
  const navigate = useNavigate()
  const [tenants, setTenants] = useState<PlatformTenant[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [search, setSearch] = useState('')
  const [licenseForm, setLicenseForm] = useState<LicenseFormState>({ ...DEFAULT_LICENSE })
  const [savingLicense, setSavingLicense] = useState(false)
  const [founderEnrolling, setFounderEnrolling] = useState(false)
  const [founderBanner, setFounderBanner] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [statusLoading, setStatusLoading] = useState(false)
  const [impersonating, setImpersonating] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<CreateTenantForm>({ ...DEFAULT_CREATE_FORM })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [brandingLabel, setBrandingLabel] = useState('')
  const [brandingSaving, setBrandingSaving] = useState(false)
  const [brandingError, setBrandingError] = useState<string | null>(null)
  const [logoUploading, setLogoUploading] = useState(false)
  const [adminForm, setAdminForm] = useState({ email: '', full_name: '', password: '' })
  const [adminCreating, setAdminCreating] = useState(false)
  const [adminMessage, setAdminMessage] = useState<string | null>(null)
  const [adminErrorMsg, setAdminErrorMsg] = useState<string | null>(null)
  const [moduleSettings, setModuleSettings] = useState<TenantModuleSettings | null>(null)
  const [modulesLoading, setModulesLoading] = useState(false)
  const [modulesSaving, setModulesSaving] = useState(false)
  const [modulesError, setModulesError] = useState<string | null>(null)
  const [roleModuleMatrix, setRoleModuleMatrix] = useState<TenantRoleModuleMatrix | null>(null)
  const [roleMatrixLoading, setRoleMatrixLoading] = useState(false)
  const [roleMatrixSaving, setRoleMatrixSaving] = useState(false)
  const [roleMatrixError, setRoleMatrixError] = useState<string | null>(null)
  const [moduleOverrideUsers, setModuleOverrideUsers] = useState<TenantModuleOverrideUser[]>([])
  const [userModuleOverrides, setUserModuleOverrides] = useState<TenantUserModuleOverrides | null>(null)
  const [selectedOverrideUserId, setSelectedOverrideUserId] = useState<string>('')
  const [userOverrideLoading, setUserOverrideLoading] = useState(false)
  const [userOverrideSaving, setUserOverrideSaving] = useState(false)
  const [userOverrideError, setUserOverrideError] = useState<string | null>(null)
  const [seatRequests, setSeatRequests] = useState<SeatRequest[]>([])
  const [seatLoading, setSeatLoading] = useState(false)
  const [seatError, setSeatError] = useState<string | null>(null)
  const [seatActionLoading, setSeatActionLoading] = useState(false)
  const [vacancyAccess, setVacancyAccess] = useState<TenantVacancyAccessItem[]>([])
  const [vacancyAccessLoading, setVacancyAccessLoading] = useState(false)
  const [vacancyAccessError, setVacancyAccessError] = useState<string | null>(null)
  const [vacancyAccessSaving, setVacancyAccessSaving] = useState(false)
  const [vacancyAccessMessage, setVacancyAccessMessage] = useState<string | null>(null)
  const [vacancySearch, setVacancySearch] = useState('')
  const [vacancyOptions, setVacancyOptions] = useState<TenantVacancyOption[]>([])
  const [vacancyOptionsLoading, setVacancyOptionsLoading] = useState(false)
  const [vacancyOptionsError, setVacancyOptionsError] = useState<string | null>(null)
  const [detailTab, setDetailTab] = useState<'overview' | 'billing' | 'access'>('overview')
  const [legalHostSettings, setLegalHostSettings] = useState<TenantLegalHostSettings>({
    public_domain: '',
    custom_domain: '',
    legal_domain: '',
    public_hosts: [],
    domains: [],
    legal_hosts: [],
  })
  const [legalHostRaw, setLegalHostRaw] = useState({ public_hosts: '', domains: '', legal_hosts: '' })
  const [legalHostLoading, setLegalHostLoading] = useState(false)
  const [legalHostSaving, setLegalHostSaving] = useState(false)
  const [legalHostError, setLegalHostError] = useState<string | null>(null)

  const selected = useMemo(() => tenants.find((t) => t.id === selectedId) ?? null, [selectedId, tenants])
  const selectedTenantId = selected?.id ?? null
  const isSuperAdmin = (me?.role || '').toLowerCase() === 'superadmin'
  const roleOrder: RoleModuleMatrixRole[] = useMemo(
    () => [
      'administrator',
      'supervisor',
      'recruiter',
      'client_manager',
      'client_processor',
      'compliance_officer',
      'hr_officer',
      'viewer',
    ],
    [],
  )
  const normalizeRoleKey = useCallback((roleValue?: string | null): RoleModuleMatrixRole => {
    const normalized = String(roleValue || '').trim().toLowerCase()
    if (normalized === 'administrator') return 'administrator'
    if (normalized === 'supervisor') return 'supervisor'
    if (normalized === 'recruiter') return 'recruiter'
    if (normalized === 'client_manager') return 'client_manager'
    if (normalized === 'client_processor') return 'client_processor'
    if (normalized === 'compliance_officer' || normalized === 'compliance' || normalized === 'docs_officer') {
      return 'compliance_officer'
    }
    if (normalized === 'hr_officer' || normalized === 'people_ops') return 'hr_officer'
    return 'viewer'
  }, [])

  const selectedOverrideUser = useMemo(
    () => moduleOverrideUsers.find((user) => user.user_id === selectedOverrideUserId) ?? null,
    [moduleOverrideUsers, selectedOverrideUserId],
  )

  const refresh = useCallback(async () => {
    if (!isSuperAdmin) return
    setLoading(true)
    setError(null)
    try {
      const params: Parameters<typeof listPlatformTenants>[0] = {}
      if (statusFilter !== 'all') params.status = [statusFilter]
      if (typeFilter !== 'all') params.tenantType = [typeFilter]
      if (search.trim()) params.search = search.trim()
      params.limit = 100
      const data = await listPlatformTenants(params)
      setTenants(data.items)
      if (!selectedId && data.items.length > 0) {
        setSelectedId(data.items[0].id)
        setLicenseForm(toLicenseForm(data.items[0].license))
      } else if (selectedId) {
        const next = data.items.find((item) => item.id === selectedId)
        if (next) {
          setLicenseForm(toLicenseForm(next.license))
        } else if (data.items.length > 0) {
          setSelectedId(data.items[0].id)
          setLicenseForm(toLicenseForm(data.items[0].license))
        } else {
          setSelectedId(null)
          setLicenseForm({ ...DEFAULT_LICENSE })
        }
      }
    } catch (err) {
      setError(formatErrorMessage(err, t('app.platform.tenants.errors.load_failed')))
    } finally {
      setLoading(false)
    }
  }, [isSuperAdmin, search, selectedId, statusFilter, t, typeFilter])

  useEffect(() => {
    refresh()
  }, [refresh])

  const fetchVacancyAccess = useCallback(async () => {
    if (!selectedTenantId || !isSuperAdmin) {
      setVacancyAccess([])
      setVacancyAccessError(null)
      setVacancyAccessLoading(false)
      return
    }
    setVacancyAccessLoading(true)
    setVacancyAccessError(null)
    try {
      const data = await listTenantVacancyAccess(selectedTenantId)
      setVacancyAccess(data.items)
    } catch (err) {
      setVacancyAccessError(formatErrorMessage(err, t('app.platform.tenants.access.errors.load_failed')))
      setVacancyAccess([])
    } finally {
      setVacancyAccessLoading(false)
    }
  }, [isSuperAdmin, selectedTenantId, t])

  useEffect(() => {
    setVacancyOptions([])
    setVacancyOptionsError(null)
    setVacancySearch('')
    setVacancyAccessMessage(null)
    if (!selectedTenantId || !isSuperAdmin) {
      setVacancyAccess([])
      setVacancyAccessLoading(false)
      return
    }
    void fetchVacancyAccess()
  }, [fetchVacancyAccess, isSuperAdmin, selectedTenantId])

  const submitVacancyAccessUpdate = useCallback(
    async (nextIds: string[]) => {
      if (!selectedTenantId) return
      setVacancyAccessSaving(true)
      setVacancyAccessError(null)
      setVacancyAccessMessage(null)
      try {
        const data = await updateTenantVacancyAccess(selectedTenantId, nextIds)
        setVacancyAccess(data.items)
        setVacancyAccessMessage(
          nextIds.length === 0
            ? t('app.platform.tenants.access.messages.cleared')
            : t('app.platform.tenants.access.messages.updated', formatValues({ count: nextIds.length })),
        )
      } catch (err) {
        setVacancyAccessError(formatErrorMessage(err, t('app.platform.tenants.access.errors.update_failed')))
      } finally {
        setVacancyAccessSaving(false)
      }
    },
    [selectedTenantId, t],
  )

  const handleRemoveSharedVacancy = useCallback(
    (vacancyId: string) => {
      if (!selectedTenantId) return
      const remaining = vacancyAccess.filter((item) => item.vacancy_id !== vacancyId).map((item) => item.vacancy_id)
      void submitVacancyAccessUpdate(remaining)
    },
    [selectedTenantId, submitVacancyAccessUpdate, vacancyAccess],
  )

  const handleAddSharedVacancy = useCallback(
    (option: TenantVacancyOption) => {
      if (!selectedTenantId) return
      if (vacancyAccess.some((item) => item.vacancy_id === option.vacancy_id)) return
      const nextIds = [...vacancyAccess.map((item) => item.vacancy_id), option.vacancy_id]
      void submitVacancyAccessUpdate(nextIds)
    },
    [selectedTenantId, submitVacancyAccessUpdate, vacancyAccess],
  )

  const handleVacancySearchSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      if (!selectedTenantId) return
      const query = vacancySearch.trim()
      if (query.length < 2) {
        setVacancyOptions([])
        setVacancyOptionsError(t('app.platform.tenants.access.search_min'))
        return
      }
      setVacancyOptionsLoading(true)
      setVacancyOptionsError(null)
      try {
        const data = await listTenantVacancyOptions(selectedTenantId, { search: query })
        setVacancyOptions(data)
        if (data.length === 0) {
          setVacancyOptionsError(t('app.platform.tenants.access.search_empty'))
        }
      } catch (err) {
        setVacancyOptionsError(formatErrorMessage(err, t('app.platform.tenants.access.errors.options_failed')))
      } finally {
        setVacancyOptionsLoading(false)
      }
    },
    [selectedTenantId, t, vacancySearch],
  )

  const clearVacancySearchResults = useCallback(() => {
    setVacancyOptions([])
    setVacancyOptionsError(null)
  }, [])

  const handleRefreshVacancyAccess = useCallback(() => {
    void fetchVacancyAccess()
  }, [fetchVacancyAccess])

  const formatVacancyStatus = useCallback(
    (status?: string | null) => {
      if (!status) return t('common.labels.not_available')
      const normalized = status.toLowerCase()
      return t(`app.platform.tenants.access.status.${normalized}`, {
        defaultValue: status.replace(/_/g, ' '),
      })
    },
    [t],
  )

  useEffect(() => {
    if (selected) {
      setLicenseForm(toLicenseForm(selected.license))
    }
  }, [selected?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setDetailTab('overview')
  }, [selected?.id])

  useEffect(() => {
    setSelectedOverrideUserId('')
    setModuleOverrideUsers([])
    setUserModuleOverrides(null)
    setUserOverrideError(null)
  }, [selected?.id])

  useEffect(() => {
    if (selected) {
      setBrandingLabel(selected.workspace_label ?? selected.name ?? '')
    } else {
      setBrandingLabel('')
    }
  }, [selected?.id, selected?.workspace_label, selected?.name])

  useEffect(() => {
    if (!selected?.id || !isSuperAdmin) return
    let cancelled = false
    const run = async () => {
      setLegalHostLoading(true)
      setLegalHostError(null)
      try {
        const data = await getPlatformTenantLegalHostSettings(selected.id)
        if (cancelled) return
        setLegalHostSettings({
          public_domain: data.public_domain || '',
          custom_domain: data.custom_domain || '',
          legal_domain: data.legal_domain || '',
          public_hosts: data.public_hosts || [],
          domains: data.domains || [],
          legal_hosts: data.legal_hosts || [],
        })
        setLegalHostRaw({
          public_hosts: (data.public_hosts || []).join(', '),
          domains: (data.domains || []).join(', '),
          legal_hosts: (data.legal_hosts || []).join(', '),
        })
      } catch (err) {
        if (!cancelled) setLegalHostError(formatErrorMessage(err, t('app.platform.tenants.errors.load_failed')))
      } finally {
        if (!cancelled) setLegalHostLoading(false)
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [isSuperAdmin, selected?.id, t])

  useEffect(() => {
    setAdminForm({ email: '', full_name: '', password: '' })
    setAdminErrorMsg(null)
    setAdminMessage(null)
  }, [selected?.id])

  useEffect(() => {
    setFounderBanner(null)
  }, [selected?.id])

  const handleSelect = (tenant: PlatformTenant) => {
    setSelectedId(tenant.id)
    setLicenseForm(toLicenseForm(tenant.license))
  }

  const handleLicenseInput = (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const target = event.target as HTMLInputElement | HTMLTextAreaElement
    const { name } = target
    const nextValue = 'checked' in target && target.type === 'checkbox' ? target.checked : target.value
    setLicenseForm((prev) => ({
      ...prev,
      [name]: nextValue,
    }))
  }

  const handleSaveLicense = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected) return
    setSavingLicense(true)
    setActionError(null)
    try {
      const payload = licenseFormToPatch(licenseForm)
      const updated = await updatePlatformTenantLicense(selected.id, payload)
      setTenants((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      setLicenseForm(toLicenseForm(updated.license))
    } catch (err) {
      setActionError(formatErrorMessage(err, t('app.platform.tenants.errors.license_save_failed')))
    } finally {
      setSavingLicense(false)
    }
  }

  const handleEnrollFounder = useCallback(async () => {
    if (!selected) return
    setFounderEnrolling(true)
    setFounderBanner(null)
    try {
      const out = await enrollPlatformTenantFounderPricing(selected.id)
      setFounderBanner({
        kind: 'ok',
        text: t('app.platform.tenants.founder.success', {
          values: { used: String(out.founder_slots_used), max: String(out.founder_slots_max) },
        }),
      })
    } catch (err) {
      setFounderBanner({
        kind: 'err',
        text: formatErrorMessage(err, t('app.platform.tenants.founder.error_fallback')),
      })
    } finally {
      setFounderEnrolling(false)
    }
  }, [selected, t])

  const handleStatusChange = async (status: TenantStatus) => {
    if (!selected) return
    setStatusLoading(true)
    setActionError(null)
    try {
      const updated = await changePlatformTenantStatus(selected.id, { status })
      setTenants((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      setLicenseForm(toLicenseForm(updated.license))
    } catch (err) {
      setActionError(formatErrorMessage(err, t('app.platform.tenants.errors.status_change_failed')))
    } finally {
      setStatusLoading(false)
    }
  }

  const handleImpersonate = async () => {
    if (!selected) return
    const confirmText = t('app.platform.tenants.actions.impersonate_confirm', formatValues({ name: selected.name }))
    if (!window.confirm(confirmText)) return
    setImpersonating(true)
    setActionError(null)
    try {
      const token = await impersonatePlatformTenant(selected.id)
      beginImpersonation()
      setToken(token.token)
      tenantSettings.set(selected.id)
      await refreshSession()
      window.location.assign(CRM_APP_PATHS.overview)
    } catch (err) {
      setActionError(formatErrorMessage(err, t('app.platform.tenants.errors.impersonate_failed')))
    } finally {
      setImpersonating(false)
    }
  }

  const handleBrandingSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected) return
    setBrandingSaving(true)
    setBrandingError(null)
    try {
      const payload = {
        workspace_label: brandingLabel.trim() || null,
      }
      const updated = await updatePlatformTenantMetadata(selected.id, payload)
      setTenants((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setBrandingError(formatErrorMessage(err, t('app.platform.tenants.errors.branding_save_failed')))
    } finally {
      setBrandingSaving(false)
    }
  }

  const parseHostList = useCallback((raw: string): string[] => {
    return raw
      .split(',')
      .map((x) => x.trim().toLowerCase())
      .map((x) => (x.includes(':') ? x.split(':', 1)[0].trim() : x))
      .filter((x, idx, arr) => !!x && arr.indexOf(x) === idx)
  }, [])

  const handleSaveLegalHosts = useCallback(async () => {
    if (!selected?.id) return
    setLegalHostSaving(true)
    setLegalHostError(null)
    try {
      const payload: TenantLegalHostSettings = {
        public_domain: String(legalHostSettings.public_domain || '').trim() || null,
        custom_domain: String(legalHostSettings.custom_domain || '').trim() || null,
        legal_domain: String(legalHostSettings.legal_domain || '').trim() || null,
        public_hosts: parseHostList(legalHostRaw.public_hosts),
        domains: parseHostList(legalHostRaw.domains),
        legal_hosts: parseHostList(legalHostRaw.legal_hosts),
      }
      const updated = await updatePlatformTenantLegalHostSettings(selected.id, payload)
      setLegalHostSettings({
        public_domain: updated.public_domain || '',
        custom_domain: updated.custom_domain || '',
        legal_domain: updated.legal_domain || '',
        public_hosts: updated.public_hosts || [],
        domains: updated.domains || [],
        legal_hosts: updated.legal_hosts || [],
      })
      setLegalHostRaw({
        public_hosts: (updated.public_hosts || []).join(', '),
        domains: (updated.domains || []).join(', '),
        legal_hosts: (updated.legal_hosts || []).join(', '),
      })
    } catch (err) {
      setLegalHostError(formatErrorMessage(err, t('app.platform.tenants.errors.save_failed')))
    } finally {
      setLegalHostSaving(false)
    }
  }, [legalHostRaw.domains, legalHostRaw.legal_hosts, legalHostRaw.public_hosts, legalHostSettings.custom_domain, legalHostSettings.legal_domain, legalHostSettings.public_domain, parseHostList, selected?.id, t])

  const handleModuleToggle = async (key: keyof TenantModuleSettings) => {
    if (!selected || !moduleSettings) return
    setModulesSaving(true)
    setModulesError(null)
    try {
      const payload: TenantModuleSettingsPatch = { [key]: !moduleSettings[key] }
      const updated = await updatePlatformTenantModules(selected.id, payload)
      setModuleSettings(updated)
    } catch (err) {
      setModulesError(formatErrorMessage(err, t('app.platform.tenants.modules.errors.update_failed')))
    } finally {
      setModulesSaving(false)
    }
  }

  const handleRoleMatrixToggle = async (
    roleKey: RoleModuleMatrixRole,
    moduleKey: keyof TenantModuleSettings,
    field: 'visible' | 'editable',
  ) => {
    if (!selected || !roleModuleMatrix) return
    const currentCell = roleModuleMatrix[roleKey]?.[moduleKey]
    if (!currentCell) return

    let nextVisible = currentCell.visible
    let nextEditable = currentCell.editable
    if (field === 'visible') {
      nextVisible = !currentCell.visible
      if (!nextVisible) nextEditable = false
    } else {
      nextEditable = !currentCell.editable
      if (nextEditable) nextVisible = true
    }

    setRoleMatrixSaving(true)
    setRoleMatrixError(null)
    try {
      const updated = await updatePlatformTenantRoleModuleMatrix(selected.id, {
        [roleKey]: {
          [moduleKey]: {
            visible: nextVisible,
            editable: nextEditable,
          },
        },
      })
      setRoleModuleMatrix(updated)
    } catch (err) {
      setRoleMatrixError(formatErrorMessage(err, t('app.platform.tenants.modules.errors.update_failed')))
    } finally {
      setRoleMatrixSaving(false)
    }
  }

  const getEffectiveUserModuleCell = useCallback(
    (moduleKey: keyof TenantModuleSettings) => {
      if (!selectedOverrideUser || !roleModuleMatrix) return { visible: false, editable: false }
      const roleKey = normalizeRoleKey(selectedOverrideUser.role)
      const roleCell = roleModuleMatrix[roleKey]?.[moduleKey] ?? { visible: false, editable: false }
      const overrideCell = selectedOverrideUser.user_id
        ? userModuleOverrides?.users?.[selectedOverrideUser.user_id]?.[moduleKey]
        : undefined
      return overrideCell ?? roleCell
    },
    [normalizeRoleKey, roleModuleMatrix, selectedOverrideUser, userModuleOverrides],
  )

  const handleUserOverrideToggle = async (
    moduleKey: keyof TenantModuleSettings,
    field: 'visible' | 'editable',
  ) => {
    if (!selected || !selectedOverrideUser?.user_id || !roleModuleMatrix) return
    const currentCell = getEffectiveUserModuleCell(moduleKey)
    let nextVisible = currentCell.visible
    let nextEditable = currentCell.editable
    if (field === 'visible') {
      nextVisible = !currentCell.visible
      if (!nextVisible) nextEditable = false
    } else {
      nextEditable = !currentCell.editable
      if (nextEditable) nextVisible = true
    }

    setUserOverrideSaving(true)
    setUserOverrideError(null)
    try {
      const updated = await updatePlatformTenantUserModuleOverrides(selected.id, {
        users: {
          [selectedOverrideUser.user_id]: {
            [moduleKey]: {
              visible: nextVisible,
              editable: nextEditable,
            },
          },
        },
      })
      setUserModuleOverrides(updated)
    } catch (err) {
      setUserOverrideError(formatErrorMessage(err, t('app.platform.tenants.modules.errors.update_failed')))
    } finally {
      setUserOverrideSaving(false)
    }
  }

  const handleClearUserOverrides = async () => {
    if (!selected || !selectedOverrideUser?.user_id) return
    setUserOverrideSaving(true)
    setUserOverrideError(null)
    try {
      const updated = await updatePlatformTenantUserModuleOverrides(selected.id, {
        users: {
          [selectedOverrideUser.user_id]: null,
        },
      })
      setUserModuleOverrides(updated)
    } catch (err) {
      setUserOverrideError(formatErrorMessage(err, t('app.platform.tenants.modules.errors.update_failed')))
    } finally {
      setUserOverrideSaving(false)
    }
  }

  const handleSeatDecision = async (request: SeatRequest, decision: 'approved' | 'rejected') => {
    if (!selected) return
    const confirmText = t('app.platform.tenants.seat_requests.actions.confirm', {
      values: {
        status: t(`app.platform.tenants.seat_requests.status.${decision}`),
        count: request.requested_count,
      },
    })
    if (!window.confirm(confirmText)) return
    const note = window.prompt(t('app.platform.tenants.seat_requests.actions.notes_prompt'), '')
    setSeatActionLoading(true)
    setSeatError(null)
    try {
      await decidePlatformSeatRequest(selected.id, request.id, {
        status: decision,
        resolution_notes: note?.trim() ? note.trim() : undefined,
      })
      await loadSeatRequests()
    } catch (err) {
      setSeatError(formatErrorMessage(err, t('app.platform.tenants.seat_requests.errors.action_failed')))
    } finally {
      setSeatActionLoading(false)
    }
  }

  const handleOpenTeam = () => {
    if (!selected) return
    navigate(`${CRM_APP_PATHS.settingsUsers}?tenant=${selected.id}`)
  }

  const handleLogoUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !selected) return
    setLogoUploading(true)
    setBrandingError(null)
    try {
      const updated = await uploadPlatformTenantLogo(selected.id, file)
      setTenants((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setBrandingError(formatErrorMessage(err, t('app.platform.tenants.errors.logo_upload_failed')))
    } finally {
      setLogoUploading(false)
      event.target.value = ''
    }
  }

  const handleCreateInput = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
    const { name } = target
    const nextValue = target instanceof HTMLInputElement && target.type === 'checkbox' ? target.checked : target.value
    if (name.startsWith('license.')) {
      const [, field] = name.split('.', 2)
      setCreateForm((prev) => ({
        ...prev,
        license: {
          ...prev.license,
          [field]: nextValue,
        },
      }))
      return
    }
    setCreateForm((prev) => ({
      ...prev,
      [name]: nextValue,
    }))
  }

  const handleCreateTenantAdmin = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected) return
    if (!adminForm.email.trim() || !adminForm.password.trim()) {
      setAdminErrorMsg(t('app.platform.tenants.admins.form.required'))
      return
    }
    setAdminCreating(true)
    setAdminErrorMsg(null)
    setAdminMessage(null)
    try {
      await createTenantAdmin(selected.id, {
        email: adminForm.email.trim(),
        full_name: adminForm.full_name.trim() || undefined,
        password: adminForm.password,
      })
      setAdminForm({ email: '', full_name: '', password: '' })
      setAdminMessage(t('app.platform.tenants.admins.success'))
    } catch (err) {
      setAdminErrorMsg(formatErrorMessage(err, t('app.platform.tenants.admins.error')))
    } finally {
      setAdminCreating(false)
    }
  }

  const handleCreateSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setCreating(true)
    setCreateError(null)
    try {
      const trimmedName = createForm.name.trim()
      const trimmedLabel = createForm.workspace_label.trim()
      const payload: PlatformTenantCreatePayload = {
        name: trimmedName,
        slug: createForm.slug.trim().toLowerCase(),
        type: createForm.type,
        status: createForm.status,
        client_portal_enabled: createForm.client_portal_enabled,
        status_sharing_allowed: createForm.status_sharing_allowed,
        workspace_label: trimmedLabel || trimmedName || undefined,
        license: licenseFormToInput(createForm.license),
      }
      const initialAdminEmail = createForm.initial_admin_email.trim()
      if (initialAdminEmail) {
        if (!createForm.initial_admin_password.trim()) {
          throw new Error(t('app.platform.tenants.errors.initial_admin_password_required'))
        }
        payload.initial_admin = {
          email: initialAdminEmail,
          full_name: createForm.initial_admin_name.trim() || undefined,
          password: createForm.initial_admin_password,
        }
      }
      if (!payload.name || !payload.slug) {
        throw new Error(t('app.platform.tenants.errors.required_fields'))
      }
      await createPlatformTenant(payload)
      setCreateOpen(false)
      setCreateForm({ ...DEFAULT_CREATE_FORM })
      refresh()
    } catch (err) {
      setCreateError(formatErrorMessage(err, t('app.platform.tenants.errors.create_failed')))
    } finally {
      setCreating(false)
    }
  }

  const loadSeatRequests = useCallback(async () => {
    if (!selectedId || !isSuperAdmin) {
      if (!isSuperAdmin) {
        setSeatRequests([])
      }
      return
    }
    setSeatLoading(true)
    setSeatError(null)
    try {
      const data = await listPlatformSeatRequests(selectedId)
      setSeatRequests(data)
    } catch (err) {
      setSeatError(formatErrorMessage(err, t('app.platform.tenants.seat_requests.errors.load_failed')))
    } finally {
      setSeatLoading(false)
    }
  }, [selectedId, isSuperAdmin, t])

  useEffect(() => {
    if (!selectedId || !isSuperAdmin) {
      if (!isSuperAdmin) setSeatRequests([])
      return
    }
    void loadSeatRequests()
  }, [loadSeatRequests, selectedId, isSuperAdmin])

  const seatCards = useMemo(() => {
    if (!selected) return []
    const license = selected.license
    return [
      {
        key: 'recruiters',
        label: t('app.platform.tenants.usage.recruiters'),
        used: selected.usage.recruiter_count,
        limit: license?.max_recruiters ?? 0,
      },
      {
        key: 'supervisors',
        label: t('app.platform.tenants.usage.supervisors'),
        used: selected.usage.supervisor_count,
        limit: license?.max_supervisors ?? 0,
      },
      {
        key: 'client_managers',
        label: t('app.platform.tenants.usage.client_managers'),
        used: selected.usage.client_manager_count,
        limit: license?.max_client_managers ?? 0,
      },
      {
        key: 'viewers',
        label: t('app.platform.tenants.usage.viewers'),
        used: selected.usage.viewer_count,
        limit: license?.max_viewers ?? 0,
      },
    ]
  }, [selected, t])
  const detailTabs = useMemo(
    () => [
      { key: 'overview' as const, label: t('app.platform.tenants.detail.tabs.overview') },
      { key: 'billing' as const, label: t('app.platform.tenants.detail.tabs.billing') },
      { key: 'access' as const, label: t('app.platform.tenants.detail.tabs.access') },
    ],
    [t],
  )
  useEffect(() => {
    if (!selected || !isSuperAdmin) {
      setModuleSettings(null)
      setModulesError(null)
      setModulesLoading(false)
      setRoleModuleMatrix(null)
      setRoleMatrixError(null)
      setRoleMatrixLoading(false)
      setModuleOverrideUsers([])
      setUserModuleOverrides(null)
      setUserOverrideError(null)
      setUserOverrideLoading(false)
      return
    }
    let cancelled = false
    setModulesLoading(true)
    setModulesError(null)
    setRoleMatrixLoading(true)
    setRoleMatrixError(null)
    setUserOverrideLoading(true)
    setUserOverrideError(null)
    getPlatformTenantModules(selected.id)
      .then((data) => {
        if (!cancelled) setModuleSettings(data)
      })
      .catch((err) => {
        if (!cancelled) {
          setModuleSettings(null)
          setModulesError(formatErrorMessage(err, t('app.platform.tenants.modules.errors.load_failed')))
        }
      })
      .finally(() => {
        if (!cancelled) setModulesLoading(false)
      })
    getPlatformTenantRoleModuleMatrix(selected.id)
      .then((data) => {
        if (!cancelled) setRoleModuleMatrix(data)
      })
      .catch((err) => {
        if (!cancelled) {
          setRoleModuleMatrix(null)
          setRoleMatrixError(formatErrorMessage(err, t('app.platform.tenants.modules.errors.load_failed')))
        }
      })
      .finally(() => {
        if (!cancelled) setRoleMatrixLoading(false)
      })
    Promise.all([
      listPlatformTenantModuleOverrideUsers(selected.id),
      getPlatformTenantUserModuleOverrides(selected.id),
    ])
      .then(([users, overrides]) => {
        if (cancelled) return
        const activeUsers = users.filter((user) => user.user_id)
        setModuleOverrideUsers(activeUsers)
        setUserModuleOverrides(overrides)
        setSelectedOverrideUserId((prev) => {
          if (!prev) return activeUsers[0]?.user_id || ''
          if (!activeUsers.some((user) => user.user_id === prev)) return activeUsers[0]?.user_id || ''
          return prev
        })
      })
      .catch((err) => {
        if (!cancelled) {
          setModuleOverrideUsers([])
          setUserModuleOverrides(null)
          setUserOverrideError(formatErrorMessage(err, t('app.platform.tenants.modules.errors.load_failed')))
        }
      })
      .finally(() => {
        if (!cancelled) setUserOverrideLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selected, isSuperAdmin, t])

  const tenantsListErrorBanner = useMemo<FriendlyErrorInfo | null>(
    () =>
      error
        ? {
            title: error,
            hint: t('app.common.retry_hint'),
          }
        : null,
    [error, t],
  )

  if (!isSuperAdmin) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
        {t('app.platform.tenants.errors.superadmin_only')}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <SettingsSubpageHeader
        backLabel={t('admin.settings.subpage.back_all')}
        kicker={t('app.platform.tenants.header_kicker')}
        title={t('app.platform.tenants.title')}
        subtitle={t('app.platform.tenants.subtitle')}
      />
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <input
            className="input w-full max-w-xs"
            placeholder={t('app.platform.tenants.filters.search')}
            autoComplete="off"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <select
            className="input w-44"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
          >
            <option value="all">{t('app.platform.tenants.filters.status.all')}</option>
            <option value="active">{t('app.platform.tenants.filters.status.active')}</option>
            <option value="trial">{t('app.platform.tenants.filters.status.trial')}</option>
            <option value="suspended">{t('app.platform.tenants.filters.status.suspended')}</option>
          </select>
          <select
            className="input w-40"
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value as TypeFilter)}
          >
            <option value="all">{t('app.platform.tenants.filters.type.all')}</option>
            <option value="agency">{t('app.platform.tenants.filters.type.agency')}</option>
            <option value="company">{t('app.platform.tenants.filters.type.company')}</option>
            <option value="platform">{t('app.platform.tenants.filters.type.platform')}</option>
          </select>
          <div className="flex flex-1 justify-end gap-2">
            <button type="button" className="btn-secondary" onClick={() => refresh()} disabled={loading}>
              {loading ? t('app.platform.tenants.actions.refreshing') : t('app.platform.tenants.actions.refresh')}
            </button>
            <button type="button" className="btn-primary" onClick={() => setCreateOpen(true)}>
              {t('app.platform.tenants.actions.create')}
            </button>
          </div>
        </div>
        {tenantsListErrorBanner && (
          <ErrorRecoveryBanner
            info={tenantsListErrorBanner}
            onRetry={() => void refresh()}
            retryLabel={t('app.platform.tenants.actions.refresh')}
            {...friendlyErrorBannerSecondary(
              tenantsListErrorBanner,
              CRM_APP_PATHS.settingsTenants,
              t('app.platform.tenants.title'),
            )}
            compact
          />
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(260px,340px),minmax(0,1fr)]">
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              {t('app.platform.tenants.table.title')}
            </h2>
            <span className="text-xs text-slate-400">{t('app.platform.tenants.table.count', formatValues({ count: tenants.length }))}</span>
          </div>
          <div className="mt-3 space-y-2 overflow-y-auto max-h-[520px] pr-1">
            {tenants.map((tenant) => {
              const isSelected = tenant.id === selected?.id
              return (
                <button
                  key={tenant.id}
                  type="button"
                  onClick={() => handleSelect(tenant)}
                  className={[
                    'w-full rounded-lg border px-3 py-3 text-left text-sm transition',
                    isSelected ? 'border-brand-400 bg-brand-50 shadow-sm' : 'border-slate-200 hover:border-brand-200',
                  ].join(' ')}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{tenant.workspace_label || tenant.name}</div>
                      <div className="text-xs text-slate-500">{tenant.slug}</div>
                      <span
                        className={[
                          'mt-2 inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold',
                          TYPE_BADGE[tenant.type],
                        ].join(' ')}
                      >
                        {t(`app.platform.tenants.type.${tenant.type}`)}
                      </span>
                    </div>
                    <span
                      className={[
                        'inline-flex rounded-md px-2 py-0.5 text-xs font-semibold',
                        STATUS_BADGE[tenant.status],
                      ].join(' ')}
                    >
                      {t(`app.platform.tenants.status.${tenant.status}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                      {tenant.license?.plan || '—'}
                    </span>
                    <span>
                      {t(
                        'app.platform.tenants.table.companies_limit',
                        formatValues({ count: tenant.license?.max_companies ?? 0 }),
                      )}
                    </span>
                    <span>
                      {t('app.platform.tenants.table.seat_summary', {
                        values: {
                          recruiters: tenant.usage.recruiter_count,
                          supervisors: tenant.usage.supervisor_count,
                        },
                      })}
                    </span>
                  </div>
                </button>
              )
            })}
            {!tenants.length && !loading && (
              <div className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-500">
                {t('app.platform.tenants.table.empty')}
              </div>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4">
          {selected ? (
            <>
              <div className="mb-4 flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{selected.name}</h3>
                  <p className="text-sm text-slate-500">
                    {t('app.platform.tenants.detail.subtitle', formatValues({ slug: selected.slug }))}
                  </p>
                  {selected.workspace_label && (
                    <p className="text-xs text-slate-500">
                      {t('app.platform.tenants.detail.workspace_label', formatValues({ label: selected.workspace_label }))}
                    </p>
                  )}
                </div>
                <span className={['inline-flex rounded-md px-2 py-0.5 text-xs font-semibold', STATUS_BADGE[selected.status]].join(' ')}>
                  {t(`app.platform.tenants.status.${selected.status}`)}
                </span>
              </div>
              <nav className="mb-4 flex flex-wrap gap-2 text-xs font-semibold text-slate-500">
                {detailTabs.map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    className={[
                      'rounded-md border px-3 py-1 transition',
                      detailTab === tab.key ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-slate-200 hover:border-brand-300 hover:text-brand-700',
                    ].join(' ')}
                    onClick={() => setDetailTab(tab.key)}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>

              <div className="rounded border border-slate-100 p-3">
                <h4 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.actions.title')}</h4>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button type="button" className="btn-secondary" onClick={handleImpersonate} disabled={impersonating}>
                    {impersonating ? t('app.platform.tenants.actions.impersonating') : t('app.platform.tenants.actions.impersonate')}
                  </button>
                  <button type="button" className="btn-secondary" onClick={handleOpenTeam}>
                    {t('app.platform.tenants.actions.manage_team')}
                  </button>
                  {selected.status === 'active' ? (
                    <button type="button" className="btn-danger" onClick={() => handleStatusChange('suspended')} disabled={statusLoading}>
                      {statusLoading ? t('app.platform.tenants.actions.updating') : t('app.platform.tenants.actions.suspend')}
                    </button>
                  ) : (
                    <button type="button" className="btn-primary" onClick={() => handleStatusChange('active')} disabled={statusLoading}>
                      {statusLoading ? t('app.platform.tenants.actions.updating') : t('app.platform.tenants.actions.activate')}
                    </button>
                  )}
                  {selected.status !== 'trial' && (
                    <button type="button" className="btn-secondary" onClick={() => handleStatusChange('trial')} disabled={statusLoading}>
                      {statusLoading ? t('app.platform.tenants.actions.updating') : t('app.platform.tenants.actions.mark_trial')}
                    </button>
                  )}
                </div>
              </div>
              {detailTab === 'overview' && (
                <div className="space-y-4 text-sm text-slate-600">
                  <div className="grid gap-3 rounded border border-slate-100 p-3">
                    <div>
                      <span className="text-xs uppercase text-slate-400">{t('app.platform.tenants.detail.type_label')}</span>
                      <div className="font-medium text-slate-900">{t(`app.platform.tenants.type.${selected.type}`)}</div>
                    </div>
                    <div>
                      <span className="text-xs uppercase text-slate-400">{t('app.platform.tenants.detail.created_at')}</span>
                      <div>{new Date(selected.created_at).toLocaleString()}</div>
                    </div>
                    <div>
                      <span className="text-xs uppercase text-slate-400">{t('app.platform.tenants.detail.client_portal')}</span>
                      <div className="font-medium text-slate-900">
                        {selected.client_portal_enabled ? t('app.platform.tenants.detail.portal_enabled') : t('app.platform.tenants.detail.portal_disabled')}
                      </div>
                    </div>
                  </div>

                  <div className="rounded border border-slate-100 p-3">
                    <h4 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.branding.title')}</h4>
                    <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <form className="flex-1 space-y-2" onSubmit={handleBrandingSubmit}>
                        <label className="text-xs font-medium text-slate-500">
                          {t('app.platform.tenants.branding.workspace_label')}
                          <input
                            className="input mt-1"
                            autoComplete="off"
                            value={brandingLabel}
                            onChange={(event) => setBrandingLabel(event.target.value)}
                            placeholder={selected.name}
                          />
                        </label>
                        {brandingError && (
                          <ErrorRecoveryBanner
                            info={{
                              title: brandingError,
                              hint: t('app.common.retry_hint'),
                            }}
                            compact
                          />
                        )}
                        <button type="submit" className="btn-primary" disabled={brandingSaving}>
                          {brandingSaving ? t('common.saving') : t('common.actions.save')}
                        </button>
                      </form>
                      <div className="flex flex-col items-center gap-2 md:w-48">
                        <img
                          src="/logo_hf.svg"
                          alt="HostFlow"
                          className="max-h-12 w-auto rounded border border-slate-200 bg-white object-contain"
                          style={{ maxHeight: 48 }}
                        />
                        <label className={`btn-secondary relative text-center ${logoUploading ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'}`}>
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/webp"
                            className="sr-only"
                            onChange={handleLogoUpload}
                            disabled={logoUploading}
                          />
                          {logoUploading ? t('app.platform.tenants.branding.uploading') : t('app.platform.tenants.branding.upload')}
                        </label>
                        <p className="text-center text-[11px] text-slate-400">{t('app.platform.tenants.branding.logo_hint')}</p>
                      </div>
                    </div>
                  </div>

                  <div className="rounded border border-slate-100 p-3">
                    <h4 className="text-sm font-semibold text-slate-900">Legal/Public Hosts</h4>
                    <p className="mt-1 text-xs text-slate-500">
                      Host mapping for dynamic `/legal/*.html` tenant resolution.
                    </p>
                    {legalHostError && (
                      <ErrorRecoveryBanner
                        info={{
                          title: legalHostError,
                          hint: t('app.common.retry_hint'),
                        }}
                        compact
                      />
                    )}
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <label className="text-xs font-medium text-slate-500">
                        public_domain
                        <input
                          className="input mt-1"
                          value={String(legalHostSettings.public_domain || '')}
                          onChange={(e) => setLegalHostSettings((prev) => ({ ...prev, public_domain: e.target.value }))}
                          placeholder="example.com"
                        />
                      </label>
                      <label className="text-xs font-medium text-slate-500">
                        legal_domain
                        <input
                          className="input mt-1"
                          value={String(legalHostSettings.legal_domain || '')}
                          onChange={(e) => setLegalHostSettings((prev) => ({ ...prev, legal_domain: e.target.value }))}
                          placeholder="legal.example.com"
                        />
                      </label>
                      <label className="text-xs font-medium text-slate-500 md:col-span-2">
                        custom_domain
                        <input
                          className="input mt-1"
                          value={String(legalHostSettings.custom_domain || '')}
                          onChange={(e) => setLegalHostSettings((prev) => ({ ...prev, custom_domain: e.target.value }))}
                          placeholder="brand.example.com"
                        />
                      </label>
                      <label className="text-xs font-medium text-slate-500 md:col-span-2">
                        public_hosts (comma-separated)
                        <input
                          className="input mt-1"
                          value={legalHostRaw.public_hosts}
                          onChange={(e) => setLegalHostRaw((prev) => ({ ...prev, public_hosts: e.target.value }))}
                          placeholder="example.com, www.example.com"
                        />
                      </label>
                      <label className="text-xs font-medium text-slate-500 md:col-span-2">
                        domains (comma-separated)
                        <input
                          className="input mt-1"
                          value={legalHostRaw.domains}
                          onChange={(e) => setLegalHostRaw((prev) => ({ ...prev, domains: e.target.value }))}
                          placeholder="example.com, jobs.example.com"
                        />
                      </label>
                      <label className="text-xs font-medium text-slate-500 md:col-span-2">
                        legal_hosts (comma-separated)
                        <input
                          className="input mt-1"
                          value={legalHostRaw.legal_hosts}
                          onChange={(e) => setLegalHostRaw((prev) => ({ ...prev, legal_hosts: e.target.value }))}
                          placeholder="legal.example.com"
                        />
                      </label>
                    </div>
                    <button type="button" className="btn-primary mt-3" onClick={() => void handleSaveLegalHosts()} disabled={legalHostSaving || legalHostLoading}>
                      {legalHostSaving ? t('common.saving') : t('common.actions.save')}
                    </button>
                  </div>

                  <div className="rounded border border-slate-100 p-3">
                    <h4 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.usage.title')}</h4>
                    <div className="mt-2 grid gap-3">
                      {seatCards.map((seat) => (
                        <SeatProgress key={seat.key} label={seat.label} used={seat.used} limit={seat.limit} t={t} />
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {detailTab === 'billing' && (
                <div className="space-y-4">
                  <div className="rounded border border-slate-100 p-3">
                    <form className="space-y-3" onSubmit={handleSaveLicense}>
                      <h4 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.license.title')}</h4>
                      {actionError && (
                        <ErrorRecoveryBanner
                          info={{
                            title: actionError,
                            hint: t('app.common.retry_hint'),
                          }}
                          compact
                        />
                      )}
                      <div className="grid gap-3 md:grid-cols-2">
                        <label className="text-xs font-medium text-slate-500">
                          {t('app.platform.tenants.license.plan')}
                          <input
                            className="input mt-1"
                            name="plan"
                            autoComplete="off"
                            value={licenseForm.plan}
                            onChange={handleLicenseInput}
                          />
                        </label>
                        <label className="text-xs font-medium text-slate-500">
                          {t('app.platform.tenants.license.expires_at')}
                          <input
                            className="input mt-1"
                            name="expires_at"
                            type="date"
                            autoComplete="off"
                            value={licenseForm.expires_at}
                            onChange={handleLicenseInput}
                          />
                        </label>
                      </div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <label className="text-xs font-medium text-slate-500">
                          {t('app.platform.tenants.license.max_recruiters')}
                          <input
                            className="input mt-1"
                            name="max_recruiters"
                            autoComplete="off"
                            value={licenseForm.max_recruiters}
                            onChange={handleLicenseInput}
                          />
                        </label>
                        <label className="text-xs font-medium text-slate-500">
                          {t('app.platform.tenants.license.max_supervisors')}
                          <input
                            className="input mt-1"
                            name="max_supervisors"
                            autoComplete="off"
                            value={licenseForm.max_supervisors}
                            onChange={handleLicenseInput}
                          />
                        </label>
                        <label className="text-xs font-medium text-slate-500">
                          {t('app.platform.tenants.license.max_client_managers')}
                          <input
                            className="input mt-1"
                            name="max_client_managers"
                            autoComplete="off"
                            value={licenseForm.max_client_managers}
                            onChange={handleLicenseInput}
                          />
                        </label>
                        <label className="text-xs font-medium text-slate-500">
                          {t('app.platform.tenants.license.max_viewers')}
                          <input
                            className="input mt-1"
                            name="max_viewers"
                            autoComplete="off"
                            value={licenseForm.max_viewers}
                            onChange={handleLicenseInput}
                          />
                        </label>
                        <label className="text-xs font-medium text-slate-500">
                          {t('app.platform.tenants.license.max_storage_gb')}
                          <input
                            className="input mt-1"
                            name="max_storage_gb"
                            autoComplete="off"
                            value={licenseForm.max_storage_gb}
                            onChange={handleLicenseInput}
                          />
                        </label>
                        <label className="text-xs font-medium text-slate-500">
                          {t('app.platform.tenants.license.max_companies')}
                          <input
                            className="input mt-1"
                            name="max_companies"
                            autoComplete="off"
                            value={licenseForm.max_companies}
                            onChange={handleLicenseInput}
                          />
                        </label>
                      </div>
                      <label className="flex items-center gap-2 text-xs font-medium text-slate-500">
                        <input type="checkbox" name="auto_renew" checked={licenseForm.auto_renew} onChange={handleLicenseInput} />
                        {t('app.platform.tenants.license.auto_renew')}
                      </label>
                      <label className="text-xs font-medium text-slate-500">
                        {t('app.platform.tenants.license.notes')}
                        <textarea className="input mt-1 min-h-[80px]" name="notes" value={licenseForm.notes} onChange={handleLicenseInput} />
                      </label>
                      <div className="flex gap-2">
                        <button type="submit" className="btn-primary" disabled={savingLicense}>
                          {savingLicense ? t('app.platform.tenants.actions.saving') : t('app.platform.tenants.actions.save_license')}
                        </button>
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => setLicenseForm(toLicenseForm(selected.license))}
                          disabled={savingLicense}
                        >
                          {t('app.platform.tenants.actions.reset')}
                        </button>
                      </div>
                    </form>
                  </div>

                  <div className="rounded border border-slate-100 p-3">
                    <h4 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.founder.title')}</h4>
                    <p className="mt-1 text-xs text-slate-500">{t('app.platform.tenants.founder.subtitle')}</p>
                    {founderBanner && (
                      <p
                        className={`mt-2 text-xs ${founderBanner.kind === 'ok' ? 'text-emerald-700' : 'text-red-600'}`}
                      >
                        {founderBanner.text}
                      </p>
                    )}
                    <button
                      type="button"
                      className="btn-secondary mt-2"
                      disabled={!selected || founderEnrolling}
                      onClick={() => void handleEnrollFounder()}
                    >
                      {founderEnrolling ? t('app.platform.tenants.founder.enrolling') : t('app.platform.tenants.founder.enroll')}
                    </button>
                  </div>

                  {isSuperAdmin && (
                    <div className="rounded border border-slate-100 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <h4 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.seat_requests.title')}</h4>
                          <p className="text-xs text-slate-500">{t('app.platform.tenants.seat_requests.subtitle')}</p>
                        </div>
                        <button type="button" className="btn-secondary btn-xs" onClick={() => void loadSeatRequests()} disabled={seatLoading}>
                          {seatLoading ? t('common.loading') : t('app.platform.tenants.seat_requests.actions.refresh')}
                        </button>
                      </div>
                      {seatError && (
                        <div className="mt-2">
                          <ErrorRecoveryBanner
                            info={{
                              title: seatError,
                              hint: t('app.common.retry_hint'),
                            }}
                            compact
                          />
                        </div>
                      )}
                      {seatLoading ? (
                        <div className="mt-4 text-xs text-slate-500">{t('common.loading')}</div>
                      ) : seatRequests.length === 0 ? (
                        <div className="mt-4 rounded border border-slate-100 bg-slate-50 px-3 py-3 text-xs text-slate-500">
                          {t('app.platform.tenants.seat_requests.empty')}
                        </div>
                      ) : (
                        <div className="mt-3 space-y-3">
                          {seatRequests.map((request) => (
                            <div key={request.id} className="rounded border border-slate-100 p-3 text-sm text-slate-700">
                              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                                <span>{new Date(request.created_at).toLocaleString()}</span>
                                <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${SEAT_STATUS_BADGE[request.status]}`}>
                                  {t(`app.platform.tenants.seat_requests.status.${request.status}`)}
                                </span>
                              </div>
                              <div className="mt-1 font-semibold">
                                {t('app.platform.tenants.seat_requests.summary', {
                                  values: {
                                    role: t(`app.settings.team.form.roles.${request.role}`),
                                    count: request.requested_count,
                                  },
                                })}
                              </div>
                              {request.message && <p className="text-xs text-slate-500">{request.message}</p>}
                              {request.resolution_notes && (
                                <p className="text-xs text-slate-400">
                                  {t('app.platform.tenants.seat_requests.resolution', { values: { notes: request.resolution_notes } })}
                                </p>
                              )}
                              {request.status === 'pending' && (
                                <div className="mt-2 flex flex-wrap gap-2">
                                  <button
                                    type="button"
                                    className="btn-primary"
                                    onClick={() => void handleSeatDecision(request, 'approved')}
                                    disabled={seatActionLoading}
                                  >
                                    {seatActionLoading ? t('common.saving') : t('app.platform.tenants.seat_requests.actions.approve')}
                                  </button>
                                  <button
                                    type="button"
                                    className="btn-danger"
                                    onClick={() => void handleSeatDecision(request, 'rejected')}
                                    disabled={seatActionLoading}
                                  >
                                    {seatActionLoading ? t('common.saving') : t('app.platform.tenants.seat_requests.actions.reject')}
                                  </button>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {detailTab === 'access' && (
                <div className="space-y-4">
                  <div className="rounded border border-slate-100 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <h4 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.access.title')}</h4>
                        <p className="text-xs text-slate-500">{t('app.platform.tenants.access.subtitle')}</p>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                          {t('app.platform.tenants.access.counter', formatValues({ count: vacancyAccess.length }))}
                        </span>
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={handleRefreshVacancyAccess}
                          disabled={vacancyAccessLoading}
                        >
                          {vacancyAccessLoading ? t('common.loading') : t('app.platform.tenants.access.actions.refresh')}
                        </button>
                      </div>
                    </div>
                    {vacancyAccessMessage && (
                      <div className="mt-2 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">{vacancyAccessMessage}</div>
                    )}
                    {vacancyAccessError && (
                      <div className="mt-2">
                        <ErrorRecoveryBanner
                          info={{
                            title: vacancyAccessError,
                            hint: t('app.common.retry_hint'),
                          }}
                          compact
                        />
                      </div>
                    )}
                    {vacancyAccessLoading ? (
                      <div className="mt-3 text-xs text-slate-500">{t('common.loading')}</div>
                    ) : vacancyAccess.length === 0 ? (
                      <div className="mt-3 rounded border border-dashed border-slate-200 px-3 py-3 text-xs text-slate-500">
                        {t('app.platform.tenants.access.empty')}
                      </div>
                    ) : (
                      <ul className="mt-3 space-y-2">
                        {vacancyAccess.map((item) => (
                          <li key={item.vacancy_id} className="flex items-start justify-between rounded border border-slate-100 bg-slate-50 px-3 py-2">
                            <div>
                              <div className="text-sm font-medium text-slate-900">{item.title}</div>
                              <div className="text-xs text-slate-500">
                                {item.company_name && <span>{item.company_name}</span>}
                                {item.company_name && item.status && <span className="mx-1">·</span>}
                                <span>{formatVacancyStatus(item.status)}</span>
                              </div>
                            </div>
                            <button
                              type="button"
                              className="btn-secondary btn-xs"
                              onClick={() => handleRemoveSharedVacancy(item.vacancy_id)}
                              disabled={vacancyAccessSaving}
                            >
                              {t('app.platform.tenants.access.actions.remove')}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                    <div className="mt-4 border-t border-slate-100 pt-4">
                      <form className="flex flex-col gap-2 sm:flex-row" onSubmit={handleVacancySearchSubmit}>
                        <input
                          className="input flex-1"
                          placeholder={t('app.platform.tenants.access.search_placeholder')}
                          autoComplete="off"
                          value={vacancySearch}
                          onChange={(event) => setVacancySearch(event.target.value)}
                        />
                        <div className="flex gap-2">
                          <button type="submit" className="btn-secondary" disabled={vacancyOptionsLoading}>
                            {vacancyOptionsLoading
                              ? t('app.platform.tenants.access.actions.searching')
                              : t('app.platform.tenants.access.actions.search')}
                          </button>
                          {vacancyOptions.length > 0 && (
                            <button type="button" className="btn-secondary btn-xs" onClick={clearVacancySearchResults}>
                              {t('app.platform.tenants.access.actions.clear_results')}
                            </button>
                          )}
                        </div>
                      </form>
                      <p className="mt-1 text-[11px] text-slate-500">{t('app.platform.tenants.access.search_hint')}</p>
                      {vacancyOptionsError && (
                        <div className="mt-2">
                          <ErrorRecoveryBanner
                            info={{
                              title: vacancyOptionsError,
                              hint: t('app.common.retry_hint'),
                            }}
                            compact
                          />
                        </div>
                      )}
                      {vacancyOptions.length > 0 && (
                        <ul className="mt-3 space-y-2">
                          {vacancyOptions.map((option) => {
                            const alreadyShared = vacancyAccess.some((entry) => entry.vacancy_id === option.vacancy_id)
                            return (
                              <li key={option.vacancy_id} className="flex items-start justify-between rounded border border-slate-100 px-3 py-2">
                                <div>
                                  <div className="text-sm font-medium text-slate-900">{option.title}</div>
                                  <div className="text-xs text-slate-500">
                                    {option.company_name && <span>{option.company_name}</span>}
                                    {option.company_name && option.status && <span className="mx-1">·</span>}
                                    <span>{formatVacancyStatus(option.status)}</span>
                                  </div>
                                </div>
                                <button
                                  type="button"
                                  className={alreadyShared ? 'btn-secondary btn-xs' : 'btn-primary text-xs'}
                                  onClick={() => handleAddSharedVacancy(option)}
                                  disabled={alreadyShared || vacancyAccessSaving}
                                >
                                  {alreadyShared
                                    ? t('app.platform.tenants.access.actions.shared')
                                    : t('app.platform.tenants.access.actions.share')}
                                </button>
                              </li>
                            )
                          })}
                        </ul>
                      )}
                    </div>
                  </div>

                  <div className="rounded border border-slate-100 p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.modules.title')}</h4>
                        <p className="text-xs text-slate-500">{t('app.platform.tenants.modules.description')}</p>
                      </div>
                      {modulesSaving && <span className="text-xs text-slate-400">{t('common.saving')}</span>}
                    </div>
                    {modulesError && (
                      <div className="mt-2">
                        <ErrorRecoveryBanner
                          info={{
                            title: modulesError,
                            hint: t('app.common.retry_hint'),
                          }}
                          compact
                        />
                      </div>
                    )}
                    {modulesLoading ? (
                      <div className="mt-3 text-xs text-slate-500">{t('common.loading')}</div>
                    ) : moduleSettings ? (
                      <div className="mt-3 grid gap-2 md:grid-cols-2">
                        {(Object.keys(moduleSettings) as Array<keyof TenantModuleSettings>).map((key) => (
                          <label key={key} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm text-slate-700">
                            <span>{t(MODULE_LABELS[key])}</span>
                            <input
                              type="checkbox"
                              className="h-4 w-4 accent-brand-600"
                              checked={moduleSettings[key]}
                              onChange={() => handleModuleToggle(key)}
                              disabled={modulesSaving}
                            />
                          </label>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-3 text-xs text-slate-500">{t('app.platform.tenants.modules.empty')}</div>
                    )}

                    <div className="mt-4 rounded border border-slate-100 p-3">
                      <div className="flex items-center justify-between">
                        <h5 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.modules.matrix_title')}</h5>
                        {roleMatrixSaving && <span className="text-xs text-slate-400">{t('common.saving')}</span>}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{t('app.platform.tenants.modules.matrix_description')}</p>
                      {roleMatrixError && (
                        <div className="mt-2">
                          <ErrorRecoveryBanner
                            info={{
                              title: roleMatrixError,
                              hint: t('app.common.retry_hint'),
                            }}
                            compact
                          />
                        </div>
                      )}
                      {roleMatrixLoading ? (
                        <div className="mt-3 text-xs text-slate-500">{t('common.loading')}</div>
                      ) : roleModuleMatrix && moduleSettings ? (
                        <div className="mt-3 overflow-x-auto">
                          <table className="min-w-full divide-y divide-slate-200 text-xs">
                            <thead>
                              <tr className="bg-slate-50 text-left text-slate-600">
                                <th className="px-2 py-2">{t('app.platform.tenants.modules.matrix_module')}</th>
                                {roleOrder.map((roleKey) => (
                                  <th key={roleKey} className="px-2 py-2">{t(`app.admin.users.roles.${roleKey}`)}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {(Object.keys(moduleSettings) as Array<keyof TenantModuleSettings>).map((moduleKey) => (
                                <tr key={moduleKey}>
                                  <td className="px-2 py-2 font-medium text-slate-700">{t(MODULE_LABELS[moduleKey])}</td>
                                  {roleOrder.map((roleKey) => {
                                    const cell = roleModuleMatrix[roleKey]?.[moduleKey]
                                    const moduleEnabled = moduleSettings[moduleKey]
                                    return (
                                      <td key={`${roleKey}:${moduleKey}`} className="px-2 py-2">
                                        <div className="flex items-center gap-2">
                                          <label className="inline-flex items-center gap-1 text-[11px] text-slate-600">
                                            <input
                                              type="checkbox"
                                              className="h-3.5 w-3.5 accent-brand-600"
                                              checked={Boolean(cell?.visible)}
                                              disabled={roleMatrixSaving || !moduleEnabled}
                                              onChange={() => handleRoleMatrixToggle(roleKey, moduleKey, 'visible')}
                                            />
                                            V
                                          </label>
                                          <label className="inline-flex items-center gap-1 text-[11px] text-slate-600">
                                            <input
                                              type="checkbox"
                                              className="h-3.5 w-3.5 accent-brand-600"
                                              checked={Boolean(cell?.editable)}
                                              disabled={roleMatrixSaving || !moduleEnabled || !cell?.visible}
                                              onChange={() => handleRoleMatrixToggle(roleKey, moduleKey, 'editable')}
                                            />
                                            E
                                          </label>
                                        </div>
                                      </td>
                                    )
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          <div className="mt-2 text-[11px] text-slate-500">
                            {t('app.platform.tenants.modules.matrix_hint')}
                          </div>
                        </div>
                      ) : (
                        <div className="mt-3 text-xs text-slate-500">{t('app.platform.tenants.modules.empty')}</div>
                      )}
                    </div>

                    <div className="mt-4 rounded border border-slate-100 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <h5 className="text-sm font-semibold text-slate-900">
                          {t('app.platform.tenants.modules.user_overrides_title')}
                        </h5>
                        {userOverrideSaving && <span className="text-xs text-slate-400">{t('common.saving')}</span>}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {t('app.platform.tenants.modules.user_overrides_description')}
                      </p>
                      {userOverrideError && (
                        <div className="mt-2">
                          <ErrorRecoveryBanner
                            info={{
                              title: userOverrideError,
                              hint: t('app.common.retry_hint'),
                            }}
                            compact
                          />
                        </div>
                      )}
                      {userOverrideLoading ? (
                        <div className="mt-3 text-xs text-slate-500">{t('common.loading')}</div>
                      ) : moduleOverrideUsers.length === 0 ? (
                        <div className="mt-3 text-xs text-slate-500">{t('app.platform.tenants.modules.empty')}</div>
                      ) : (
                        <>
                          <div className="mt-3 flex flex-wrap items-center gap-2">
                            <select
                              className="input min-w-[280px] text-sm"
                              value={selectedOverrideUserId}
                              onChange={(event) => setSelectedOverrideUserId(event.target.value)}
                              disabled={userOverrideSaving}
                            >
                              {moduleOverrideUsers.map((user) => (
                                <option key={user.user_id || user.email} value={user.user_id || ''}>
                                  {(user.full_name || user.email) + ' (' + t(`app.admin.users.roles.${user.role}`) + ')'}
                                </option>
                              ))}
                            </select>
                            <button
                              type="button"
                              className="btn-secondary btn-xs"
                              onClick={handleClearUserOverrides}
                              disabled={userOverrideSaving || !selectedOverrideUser?.user_id}
                            >
                              {t('app.platform.tenants.modules.user_overrides_reset')}
                            </button>
                          </div>
                          {selectedOverrideUser && roleModuleMatrix && moduleSettings ? (
                            <div className="mt-3 overflow-x-auto">
                              <table className="min-w-full divide-y divide-slate-200 text-xs">
                                <thead>
                                  <tr className="bg-slate-50 text-left text-slate-600">
                                    <th className="px-2 py-2">{t('app.platform.tenants.modules.matrix_module')}</th>
                                    <th className="px-2 py-2">{t('app.platform.tenants.modules.user_overrides_mode')}</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {(Object.keys(moduleSettings) as Array<keyof TenantModuleSettings>).map((moduleKey) => {
                                    const moduleEnabled = moduleSettings[moduleKey]
                                    const roleKey = normalizeRoleKey(selectedOverrideUser.role)
                                    const roleCell = roleModuleMatrix[roleKey]?.[moduleKey] ?? { visible: false, editable: false }
                                    const effectiveCell = getEffectiveUserModuleCell(moduleKey)
                                    const hasOverride = Boolean(
                                      selectedOverrideUser.user_id &&
                                        userModuleOverrides?.users?.[selectedOverrideUser.user_id]?.[moduleKey],
                                    )
                                    return (
                                      <tr key={`user-override-${moduleKey}`}>
                                        <td className="px-2 py-2 font-medium text-slate-700">{t(MODULE_LABELS[moduleKey])}</td>
                                        <td className="px-2 py-2">
                                          <div className="flex items-center gap-2">
                                            <label className="inline-flex items-center gap-1 text-[11px] text-slate-600">
                                              <input
                                                type="checkbox"
                                                className="h-3.5 w-3.5 accent-brand-600"
                                                checked={Boolean(effectiveCell.visible)}
                                                disabled={userOverrideSaving || !moduleEnabled}
                                                onChange={() => handleUserOverrideToggle(moduleKey, 'visible')}
                                              />
                                              V
                                            </label>
                                            <label className="inline-flex items-center gap-1 text-[11px] text-slate-600">
                                              <input
                                                type="checkbox"
                                                className="h-3.5 w-3.5 accent-brand-600"
                                                checked={Boolean(effectiveCell.editable)}
                                                disabled={userOverrideSaving || !moduleEnabled || !effectiveCell.visible}
                                                onChange={() => handleUserOverrideToggle(moduleKey, 'editable')}
                                              />
                                              E
                                            </label>
                                            <span className="text-[11px] text-slate-500">
                                              {hasOverride
                                                ? t('app.platform.tenants.modules.user_overrides_custom')
                                                : t('app.platform.tenants.modules.user_overrides_from_role', {
                                                    values: {
                                                      visible: roleCell.visible ? 'V' : '—',
                                                      editable: roleCell.editable ? 'E' : '—',
                                                    },
                                                  })}
                                            </span>
                                          </div>
                                        </td>
                                      </tr>
                                    )
                                  })}
                                </tbody>
                              </table>
                            </div>
                          ) : null}
                        </>
                      )}
                    </div>
                  </div>

                  <div className="rounded border border-slate-100 p-3">
                    <h4 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.admins.title')}</h4>
                    <p className="text-xs text-slate-500">{t('app.platform.tenants.admins.subtitle')}</p>
                    {adminMessage && (
                      <div className="mt-2 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">{adminMessage}</div>
                    )}
                    {adminErrorMsg && (
                      <div className="mt-2">
                        <ErrorRecoveryBanner
                          info={{
                            title: adminErrorMsg,
                            hint: t('app.common.retry_hint'),
                          }}
                          compact
                        />
                      </div>
                    )}
                    <form className="mt-3 grid gap-2 sm:grid-cols-2" onSubmit={handleCreateTenantAdmin}>
                      <label className="text-xs font-medium text-slate-500">
                        {t('app.platform.tenants.admins.form.email')}
                        <input
                          className="input mt-1"
                          type="email"
                          autoComplete="email"
                          value={adminForm.email}
                          onChange={(event) => setAdminForm((prev) => ({ ...prev, email: event.target.value }))}
                        />
                      </label>
                      <label className="text-xs font-medium text-slate-500">
                        {t('app.platform.tenants.admins.form.full_name')}
                        <input
                          className="input mt-1"
                          autoComplete="name"
                          value={adminForm.full_name}
                          onChange={(event) => setAdminForm((prev) => ({ ...prev, full_name: event.target.value }))}
                        />
                      </label>
                      <label className="text-xs font-medium text-slate-500 sm:col-span-2">
                        {t('app.platform.tenants.admins.form.password')}
                        <input
                          className="input mt-1"
                          type="password"
                          autoComplete="new-password"
                          value={adminForm.password}
                          onChange={(event) => setAdminForm((prev) => ({ ...prev, password: event.target.value }))}
                        />
                      </label>
                      <div className="sm:col-span-2">
                        <button type="submit" className="btn-secondary" disabled={adminCreating}>
                          {adminCreating ? t('common.saving') : t('app.platform.tenants.admins.form.submit')}
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="py-20 text-center text-sm text-slate-500">{t('app.platform.tenants.detail.empty')}</div>
          )}
        </section>
      </div>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title={t('app.platform.tenants.create.title')}>
        <form className="space-y-3" onSubmit={handleCreateSubmit}>
          {createError && (
            <ErrorRecoveryBanner
              info={{
                title: createError,
                hint: t('app.common.retry_hint'),
              }}
              compact
            />
          )}
          <label className="text-xs font-medium text-slate-500">
            {t('app.platform.tenants.create.name')}
            <input className="input mt-1" name="name" autoComplete="organization" value={createForm.name} onChange={handleCreateInput} />
          </label>
          <label className="text-xs font-medium text-slate-500">
            {t('app.platform.tenants.create.workspace_label')}
            <input
              className="input mt-1"
              name="workspace_label"
              autoComplete="off"
              value={createForm.workspace_label}
              onChange={handleCreateInput}
              placeholder={createForm.name || undefined}
            />
          </label>
          <label className="text-xs font-medium text-slate-500">
            {t('app.platform.tenants.create.slug')}
            <input className="input mt-1" name="slug" autoComplete="off" value={createForm.slug} onChange={handleCreateInput} />
          </label>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-xs font-medium text-slate-500">
              {t('app.platform.tenants.create.initial_admin_email')}
              <input
                className="input mt-1"
                name="initial_admin_email"
                type="email"
                autoComplete="email"
                value={createForm.initial_admin_email}
                onChange={handleCreateInput}
              />
            </label>
            <label className="text-xs font-medium text-slate-500">
              {t('app.platform.tenants.create.initial_admin_name')}
              <input
                className="input mt-1"
                name="initial_admin_name"
                autoComplete="name"
                value={createForm.initial_admin_name}
                onChange={handleCreateInput}
              />
            </label>
          </div>
          <label className="text-xs font-medium text-slate-500">
            {t('app.platform.tenants.create.initial_admin_password')}
            <input
              className="input mt-1"
              type="password"
              name="initial_admin_password"
              autoComplete="new-password"
              value={createForm.initial_admin_password}
              onChange={handleCreateInput}
            />
          </label>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-xs font-medium text-slate-500">
              {t('app.platform.tenants.create.type')}
              <select className="input mt-1" name="type" value={createForm.type} onChange={handleCreateInput}>
                <option value="agency">{t('app.platform.tenants.type.agency')}</option>
                <option value="company">{t('app.platform.tenants.type.company')}</option>
                <option value="platform">{t('app.platform.tenants.type.platform')}</option>
              </select>
            </label>
            <label className="text-xs font-medium text-slate-500">
              {t('app.platform.tenants.create.status')}
              <select className="input mt-1" name="status" value={createForm.status} onChange={handleCreateInput}>
                <option value="active">{t('app.platform.tenants.status.active')}</option>
                <option value="trial">{t('app.platform.tenants.status.trial')}</option>
                <option value="suspended">{t('app.platform.tenants.status.suspended')}</option>
              </select>
            </label>
          </div>
          <label className="flex items-center gap-2 text-xs font-medium text-slate-500">
            <input type="checkbox" name="client_portal_enabled" checked={createForm.client_portal_enabled} onChange={handleCreateInput} />
            {t('app.platform.tenants.create.portal')}
          </label>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-xs font-medium text-slate-500">
              {t('app.platform.tenants.license.plan')}
              <input className="input mt-1" name="license.plan" autoComplete="off" value={createForm.license.plan} onChange={handleCreateInput} />
            </label>
            <label className="text-xs font-medium text-slate-500">
              {t('app.platform.tenants.license.expires_at')}
              <input
                className="input mt-1"
                type="date"
                name="license.expires_at"
                autoComplete="off"
                value={createForm.license.expires_at}
                onChange={handleCreateInput}
              />
            </label>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {['max_recruiters', 'max_supervisors', 'max_client_managers', 'max_viewers', 'max_storage_gb', 'max_companies'].map((field) => (
              <label key={field} className="text-xs font-medium text-slate-500">
                {t(`app.platform.tenants.license.${field}` as const)}
                <input
                  className="input mt-1"
                  name={`license.${field}`}
                  autoComplete="off"
                  value={(createForm.license as any)[field]}
                  onChange={handleCreateInput}
                />
              </label>
            ))}
          </div>
          <label className="flex items-center gap-2 text-xs font-medium text-slate-500">
            <input type="checkbox" name="license.auto_renew" checked={createForm.license.auto_renew} onChange={handleCreateInput} />
            {t('app.platform.tenants.license.auto_renew')}
          </label>
          <label className="text-xs font-medium text-slate-500">
            {t('app.platform.tenants.license.notes')}
            <textarea className="input mt-1 min-h-[80px]" name="license.notes" value={createForm.license.notes} onChange={handleCreateInput} />
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={() => setCreateOpen(false)} disabled={creating}>
              {t('app.platform.tenants.actions.cancel')}
            </button>
            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? t('app.platform.tenants.actions.creating') : t('app.platform.tenants.actions.create')}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
