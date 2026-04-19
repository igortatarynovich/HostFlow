import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, Navigate, useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import { PublicPageShell } from './components/PublicPageShell'
import { IntakeProgressBar } from './components/IntakeProgressBar'
import { AutosaveIndicator } from './components/AutosaveIndicator'
import { LegalLinksBlock } from './components/LegalLinksBlock'
import { QrCodeCanvas } from '../../components/public/QrCodeCanvas'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { PublicLogo } from '../../components/public/PublicLogo'
import Select from '../../components/controls/Select'
import { buildCountryOptions } from '../../data/countries'
import { usePublicIntake } from '../../modules/public-intake/usePublicIntake'
import type { IntakeData, IntakeEmployment } from '../../api/publicIntake'
import { presignPublicDocument, uploadPublicDocument, updatePublicIntake } from '../../api/publicIntake'
import { subscribeToNotifications } from '../../api/publicNotifications'
import http from '../../api/http'
import { CONSENT_DOCUMENT_VERSIONS } from './constants'
import { isCookieConsentGranted } from '../../components/public/cookieConsent'
import { useRobotsMeta } from '../../hooks/useRobotsMeta'
import type {
  IntakeStep,
  QuestionId,
  DocumentStatus,
  DocumentType,
  QuestionAnswer,
  EmploymentEntry,
  DocumentEntry,
} from '../../modules/public-intake/types'

export default function PublicIntakeNew() {
  useRobotsMeta({ index: false, follow: false })
  const { token } = useParams<{ token: string }>()
  const [searchParams] = useSearchParams()
  const { t, locale, setLocale } = useI18n()
  const navigate = useNavigate()
  const { notify } = useToast()
  const telegramBotUrl = (import.meta.env.VITE_TELEGRAM_BOT_URL as string | undefined)?.trim() || 'https://t.me/HostFlow_asystent_bot'
  
  // Интеграция с API
  const {
    loading: apiLoading,
    saving: apiSaving,
    submitting,
    error: apiError,
    state: apiState,
    formData: apiFormData,
    refresh,
    updateContacts: apiUpdateContacts,
    updatePersonal: apiUpdatePersonal,
    updateExperience: apiUpdateExperience,
    upsertEmployment: apiUpsertEmployment,
    removeEmployment: apiRemoveEmployment,
    updateAgreements: apiUpdateAgreements,
    submit: apiSubmit,
  } = usePublicIntake(token)
  
  // Состояние шага
  const [currentStep, setCurrentStep] = useState<IntakeStep>('language')
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  
  // Локальные данные формы (синхронизируются с API)
  const [contacts, setContacts] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    phone_country_code: '+48',
    email: '',
  })
  
  const [answers, setAnswers] = useState<QuestionAnswer[]>([])
  const [employments, setEmployments] = useState<EmploymentEntry[]>([])
  const [documents, setDocuments] = useState<Partial<Record<DocumentType, DocumentEntry>>>({})
  
  // Состояние загрузки документов
  const [docUploading, setDocUploading] = useState<Record<string, boolean>>({})
  const [docUploadErrors, setDocUploadErrors] = useState<Record<string, string | null>>({})
  
  // Локальные ошибки
  const [error, setError] = useState<string | null>(null)
  const [subscribeNotifications, setSubscribeNotifications] = useState(true)
  
  // Флаг для отслеживания первой загрузки
  const [dataRestored, setDataRestored] = useState(false)
  const documentsOnlyMode = searchParams.get('mode') === 'documents'

  const clientIntakeTopBanner = useMemo(() => {
    if (String(apiFormData.application_kind || '').toLowerCase() !== 'client') return undefined
    return (
      <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-slate-800">
        {t('public.intake.client_mode_banner')}
      </div>
    )
  }, [apiFormData.application_kind, t])
  
  // Восстановление данных из API при первой загрузке
  useEffect(() => {
    if (apiState && apiFormData && !dataRestored && !apiLoading) {
      // Восстанавливаем контакты только если они пустые локально
      if (!contacts.first_name && !contacts.last_name && apiFormData.contacts) {
        const nameParts = (apiFormData.personal?.full_name || '').split(' ').filter(Boolean)
        setContacts({
          first_name: nameParts[0] || '',
          last_name: nameParts.slice(1).join(' ') || '',
          phone: apiFormData.contacts.phone || '',
          phone_country_code: apiFormData.contacts.phone_country_code || '+48',
          email: apiFormData.contacts.email || '',
        })
      }
      
      // Восстанавливаем ответы на вопросы только если они пустые
      if (answers.length === 0) {
        const restoredAnswers: QuestionAnswer[] = []
        if (apiFormData.personal?.citizenship) {
          restoredAnswers.push({ questionId: 'citizenship', value: apiFormData.personal.citizenship })
        }
        if (apiFormData.personal?.residency_status) {
          restoredAnswers.push({ questionId: 'stay_basis', value: apiFormData.personal.residency_status })
        }
        if (apiFormData.personal?.in_poland !== null && apiFormData.personal?.in_poland !== undefined) {
          restoredAnswers.push({ questionId: 'location', value: apiFormData.personal.in_poland ? 'in_poland' : 'not_in_poland' })
        }
        if (apiFormData.experience?.years_ce) {
          restoredAnswers.push({ questionId: 'ce_experience', value: apiFormData.experience.years_ce })
        }
        if (apiFormData.experience?.trailer_types && apiFormData.experience.trailer_types.length > 0) {
          restoredAnswers.push({ questionId: 'trailer_types', value: apiFormData.experience.trailer_types })
        }
        if (apiFormData.experience?.intl_experience !== null && apiFormData.experience?.intl_experience !== undefined) {
          restoredAnswers.push({ questionId: 'intl_experience', value: apiFormData.experience.intl_experience })
        }
        if (apiFormData.personal?.has_adr !== null && apiFormData.personal?.has_adr !== undefined) {
          restoredAnswers.push({ questionId: 'has_adr', value: apiFormData.personal.has_adr ? 'yes' : 'no' })
          // ВАЖНО: Восстанавливаем локальное состояние hasAdr
          setHasAdr(apiFormData.personal.has_adr)
        }
        if (apiFormData.personal?.birth_date) {
          restoredAnswers.push({ questionId: 'birth_date', value: apiFormData.personal.birth_date })
        }
        if (restoredAnswers.length > 0) {
          setAnswers(restoredAnswers)
        }
      }
      
      // Восстанавливаем работодателей только если они пустые
      if (employments.length === 0 && apiFormData.employments && apiFormData.employments.length > 0) {
        const restoredEmployments: EmploymentEntry[] = apiFormData.employments.map(emp => ({
          id: emp.id,
          employer_name: emp.employer_name,
          country: emp.country || '',
          position: emp.position || '',
          start_date: emp.start_date,
          end_date: emp.end_date || null,
          currently_employed: !emp.end_date, // Если нет end_date, значит работает сейчас
        }))
        setEmployments(restoredEmployments)
      }
      
      // Если анкета уже отправлена, переходим в обзор
      if (apiState.status === 'submitted') {
        setCurrentStep('overview')
      }
      
      setDataRestored(true)
    }
  }, [apiState, apiFormData, apiLoading, dataRestored, contacts.first_name, contacts.last_name, answers.length, employments.length])

  // Логика для документов - объявляем ВСЕ хуки ПЕРЕД условными возвратами
  const [currentDocumentIndex, setCurrentDocumentIndex] = useState(0)
  const [hasLicenseWith95, setHasLicenseWith95] = useState<boolean | null>(null)
  const [hasAdr, setHasAdr] = useState<boolean | null>(null)

  // Порядок документов (динамический, зависит от ответов)
  const documentFlow = useMemo(() => {
    const flow: Array<{ type: DocumentType; required: boolean }> = []
    
    // Права
    if (hasLicenseWith95 === true) {
      flow.push({ type: 'driver_license_code95', required: true })
    } else if (hasLicenseWith95 === false) {
      flow.push({ type: 'driver_license', required: true })
      flow.push({ type: 'code95', required: true })
    }
    
    // Остальные обязательные
    flow.push({ type: 'tachograph_card', required: true })
    flow.push({ type: 'residence_permit', required: true })
    flow.push({ type: 'voivodeship_decision', required: true })
    flow.push({ type: 'passport', required: true })
    flow.push({ type: 'psych_tests', required: true })
    
    // ADR (опциональный)
    if (hasAdr === true) {
      flow.push({ type: 'adr', required: false })
    }
    
    return flow
  }, [hasLicenseWith95, hasAdr])

  const getCurrentDocument = useCallback(() => {
    // Если еще не ответили на вопрос о правах
    if (hasLicenseWith95 === null) {
      return null // Показываем вопрос
    }
    
    // Если дошли до конца обязательных документов и еще не ответили на вопрос об ADR
    if (currentDocumentIndex >= documentFlow.length && hasAdr === null) {
      return null // Показываем вопрос об ADR
    }
    
    // Если индекс выходит за границы - значит все документы обработаны
    if (currentDocumentIndex >= documentFlow.length) {
      return null
    }
    
    return documentFlow[currentDocumentIndex]
  }, [hasLicenseWith95, currentDocumentIndex, documentFlow, hasAdr])

  // Список вопросов
  const questions: Array<{ id: QuestionId; type: 'select' | 'multiselect' | 'number' | 'date' }> = useMemo(() => [
    { id: 'location', type: 'select' },
    { id: 'citizenship', type: 'select' },
    { id: 'stay_basis', type: 'select' },
    { id: 'ce_experience', type: 'number' },
    { id: 'trailer_types', type: 'multiselect' },
    { id: 'frigo_experience', type: 'select' },
    { id: 'intl_experience', type: 'select' },
    { id: 'has_adr', type: 'select' },
    { id: 'birth_date', type: 'date' },
  ], [])

  // Обработчики для блока опыта работы - объявляем ВСЕ хуки ПЕРЕД условными возвратами
  const [employmentDraft, setEmploymentDraft] = useState<EmploymentEntry>({
    employer_name: '',
    country: '',
    position: '',
    start_date: new Date().toISOString().split('T')[0],
    end_date: null,
    currently_employed: false,
  })

  // Проверка языка из localStorage
  useEffect(() => {
    const savedLocale = localStorage.getItem('intake_locale')
    if (savedLocale && ['ru', 'en', 'pl'].includes(savedLocale)) {
      setLocale(savedLocale as 'ru' | 'en' | 'pl')
      setCurrentStep('contacts')
    }
  }, [setLocale])

  useEffect(() => {
    if (documentsOnlyMode) {
      setCurrentStep('documents')
    }
  }, [documentsOnlyMode])

  const docUrlFocusAppliedRef = useRef<string | null>(null)
  useEffect(() => {
    const raw = searchParams.get('doc')?.trim()
    if (!raw) {
      docUrlFocusAppliedRef.current = null
      return
    }
    if (currentStep !== 'documents') return
    if (hasLicenseWith95 === null) return
    if (docUrlFocusAppliedRef.current === raw) return
    const idx = documentFlow.findIndex((d) => d.type === raw)
    if (idx < 0) return
    setCurrentDocumentIndex(idx)
    docUrlFocusAppliedRef.current = raw
  }, [currentStep, documentFlow, hasLicenseWith95, searchParams])

  // Получение текущего ответа на вопрос
  const getCurrentAnswer = useCallback(() => {
    if (currentQuestionIndex >= questions.length) return undefined
    const question = questions[currentQuestionIndex]
    if (!question) return undefined
    const answer = answers.find(a => a.questionId === question.id)
    return answer?.value
  }, [currentQuestionIndex, answers, questions])

  // Опции для вопросов - объявляем ВСЕ useMemo ПЕРЕД условными возвратами
  const countryOptions = useMemo(() => buildCountryOptions(locale), [locale])
  
  const locationOptions = useMemo(() => [
    { value: 'in_poland', label: t('public.intake.new.questions.location.options.in_poland') },
    { value: 'not_in_poland', label: t('public.intake.new.questions.location.options.not_in_poland') },
    { value: 'other', label: t('public.intake.new.questions.location.options.other') },
  ], [t])

  const stayBasisOptions = useMemo(() => [
    { value: 'visa', label: t('public.intake.new.questions.stay_basis.options.visa') },
    { value: 'karta_pobytu', label: t('public.intake.new.questions.stay_basis.options.karta_pobytu') },
    { value: 'in_process', label: t('public.intake.new.questions.stay_basis.options.in_process') },
    { value: 'none', label: t('public.intake.new.questions.stay_basis.options.none') },
    { value: 'eu_citizen', label: t('public.intake.new.questions.stay_basis.options.eu_citizen') },
  ], [t])

  const ceExperienceOptions = useMemo(() => [
    { value: '0', label: t('public.intake.new.questions.ce_experience.options.0') },
    { value: '1-2', label: t('public.intake.new.questions.ce_experience.options.1-2') },
    { value: '3-5', label: t('public.intake.new.questions.ce_experience.options.3-5') },
    { value: '5-10', label: t('public.intake.new.questions.ce_experience.options.5-10') },
    { value: '10+', label: t('public.intake.new.questions.ce_experience.options.10+') },
  ], [t])

  const trailerTypeOptions = useMemo(() => [
    { value: 'mega', label: t('public.intake.new.questions.trailer_types.options.mega') },
    { value: 'standard', label: t('public.intake.new.questions.trailer_types.options.standard') },
    { value: 'platform', label: t('public.intake.new.questions.trailer_types.options.platform') },
    { value: 'frigo', label: t('public.intake.new.questions.trailer_types.options.frigo') },
    { value: 'tent', label: t('public.intake.new.questions.trailer_types.options.tent') },
    { value: 'container', label: t('public.intake.new.questions.trailer_types.options.container') },
    { value: 'tandem', label: t('public.intake.new.questions.trailer_types.options.tandem') },
    { value: 'car_transporter', label: t('public.intake.new.questions.trailer_types.options.car_transporter') },
  ], [t])

  const yesNoOptions = useMemo(() => [
    { value: 'yes', label: t('common.yes') },
    { value: 'no', label: t('common.no') },
  ], [t])

  // Преобразование локальных данных в формат API
  const buildIntakeData = useCallback((): IntakeData => {
    // Используем актуальные значения из refs для избежания лишних пересозданий
    const currentAnswers = answersRef.current
    const currentContacts = contactsRef.current
    const currentEmployments = employmentsRef.current
    
    // Собираем ответы на вопросы
    const locationAnswer = currentAnswers.find(a => a.questionId === 'location')
    const citizenshipAnswer = currentAnswers.find(a => a.questionId === 'citizenship')
    const stayBasisAnswer = currentAnswers.find(a => a.questionId === 'stay_basis')
    const ceExperienceAnswer = currentAnswers.find(a => a.questionId === 'ce_experience')
    const trailerTypesAnswer = currentAnswers.find(a => a.questionId === 'trailer_types')
    const frigoAnswer = currentAnswers.find(a => a.questionId === 'frigo_experience')
    const intlAnswer = currentAnswers.find(a => a.questionId === 'intl_experience')
    const hasAdrAnswer = currentAnswers.find(a => a.questionId === 'has_adr')
    const birthDateAnswer = currentAnswers.find(a => a.questionId === 'birth_date')
    
    // Преобразуем опыт CE - бэкенд требует целое число (integer)
    let yearsCe: number | null = null
    if (ceExperienceAnswer) {
      const value = ceExperienceAnswer.value
      if (typeof value === 'number') {
        yearsCe = Math.round(value) // Округляем до целого
      } else if (typeof value === 'string') {
        if (value === '0') yearsCe = 0
        else if (value === '1-2') yearsCe = 2 // Округляем до целого (берем верхнюю границу)
        else if (value === '3-5') yearsCe = 4
        else if (value === '5-10') yearsCe = 8 // Округляем до целого (берем верхнюю границу)
        else if (value === '10+') yearsCe = 10
        else {
          const parsed = parseFloat(value)
          if (!isNaN(parsed)) yearsCe = Math.round(parsed) // Округляем до целого
        }
      }
    }
    
    // Преобразуем frigo_experience
    let frigoExperience: boolean | null = null
    if (frigoAnswer?.value === 'yes') frigoExperience = true
    else if (frigoAnswer?.value === 'no') frigoExperience = false
    
    // Преобразуем has_adr
    let hasAdr: boolean | null = null
    if (hasAdrAnswer?.value === 'yes') hasAdr = true
    else if (hasAdrAnswer?.value === 'no') hasAdr = false
    
    // Преобразуем current_location
    let currentLocation: string | null = null
    if (locationAnswer?.value) {
      currentLocation = locationAnswer.value === 'in_poland' ? 'in_poland' 
        : locationAnswer.value === 'not_in_poland' ? 'not_in_poland'
        : locationAnswer.value === 'other' ? 'other'
        : String(locationAnswer.value)
    }
    
    // Преобразуем работодателей
    const intakeEmployments: IntakeEmployment[] = currentEmployments
      .filter(emp => emp.employer_name && emp.employer_name.trim()) // Фильтруем пустые
      .map(emp => {
        // Валидация country - должен быть ровно 2 символа или null
        let countryValue: string | null = null
        if (emp.country) {
          const countryStr = typeof emp.country === 'string' ? emp.country.trim().toUpperCase() : String(emp.country).trim().toUpperCase()
          countryValue = countryStr.length === 2 ? countryStr : null
        }
        
        return {
          employer_name: emp.employer_name.trim(), // Бэкенд требует непустое значение
          country: countryValue,
          position: emp.position?.trim() || null,
          // ВАЖНО: start_date и end_date должны быть строками в формате 'YYYY-MM-DD'
          start_date: typeof emp.start_date === 'string' ? emp.start_date : (emp.start_date ? String(emp.start_date) : new Date().toISOString().split('T')[0]),
          end_date: emp.currently_employed ? null : (emp.end_date ? (typeof emp.end_date === 'string' ? emp.end_date : String(emp.end_date)) : null),
          // Бэкенд ожидает эти поля, но они опциональны
          trailer_types: [],
          route_types: [],
        }
      })
    
    const fullName = `${currentContacts.first_name} ${currentContacts.last_name}`.trim()
    
    return {
      contacts: {
        phone_country_code: currentContacts.phone_country_code?.trim() || null,
        phone: currentContacts.phone?.trim() || null,
        email: currentContacts.email?.trim() || null,
        preferred_messenger: 'whatsapp',
      },
      personal: {
        full_name: fullName || null,
        citizenship: (() => {
          const val = citizenshipAnswer?.value
          if (!val) return null
          const str = typeof val === 'string' ? val.trim().toUpperCase() : String(val).trim().toUpperCase()
          // Бэкенд требует ровно 2 символа для кода страны
          return str.length === 2 ? str : null
        })(),
        residency_status: (() => {
          const val = stayBasisAnswer?.value
          if (!val) return null
          return typeof val === 'string' ? val.trim() : String(val).trim()
        })(),
        in_poland: locationAnswer?.value === 'in_poland' ? true : locationAnswer?.value === 'not_in_poland' ? false : null,
        birth_date: (() => {
          const val = birthDateAnswer?.value
          if (!val) return null
          if (typeof val === 'string') return val.trim()
          // Если это Date объект, преобразуем в ISO строку
          if (val instanceof Date) return val.toISOString().split('T')[0]
          return String(val).trim()
        })(),
        current_location: currentLocation,
        frigo_experience: frigoExperience,
        has_adr: hasAdr,
      },
      experience: {
        // ВАЖНО: years_ce должен быть целым числом (int) или null, не float!
        years_ce: yearsCe !== null ? Math.round(yearsCe) : null,
        intl_experience: (() => {
          const val = intlAnswer?.value
          if (val === true || val === 'yes') return true
          if (val === false || val === 'no') return false
          return null
        })(),
        // ВАЖНО: trailer_types и route_types должны быть массивами строк
        trailer_types: Array.isArray(trailerTypesAnswer?.value) 
          ? trailerTypesAnswer.value.filter((v): v is string => typeof v === 'string')
          : [],
        route_types: [],
      },
      employments: intakeEmployments,
      agreements: {
        general: false,
        employer_share: false,
        terms_acceptance: false,
        cookies_accepted: isCookieConsentGranted(),
      },
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Пустые зависимости - используем refs для актуальных значений

  // Автосохранение через API - используем один вызов updatePublicIntake вместо множественных
  const saveDebounceTimer = useRef<number | null>(null)
  
  // Загрузка файлов документа - объявляем ДО условных возвратов!
  const uploadDocumentFiles = useCallback(async (docType: DocumentType, files: File[]) => {
    if (!token) {
      setError(t('public.intake.new.errors.no_token'))
      return
    }
    
    // Проверка размера файлов перед загрузкой (максимум 20MB на файл)
    const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20MB
    for (const file of files) {
      if (file.size > MAX_FILE_SIZE) {
        const errorMsg = `Файл "${file.name}" слишком большой (${(file.size / 1024 / 1024).toFixed(1)} МБ). Максимальный размер: 20 МБ.`
        setDocUploadErrors(prev => ({ ...prev, [docType]: errorMsg }))
        setError(errorMsg)
        return
      }
    }
    
    setDocUploading(prev => ({ ...prev, [docType]: true }))
    setDocUploadErrors(prev => ({ ...prev, [docType]: null }))
    setError(null)
    
    try {
      // Загружаем каждый файл
      for (const file of files) {
        // Получаем presign URL
        const presign = await presignPublicDocument(token, {
          doc_type: docType,
          filename: file.name,
        })
        
        // Загружаем файл через axios
        // Presign URL содержит /api/v1, но axios уже добавляет baseURL с /api/v1
        // Поэтому нужно убрать /api/v1 из начала URL
        const uploadUrl = presign.url.startsWith('/api/v1/') 
          ? presign.url.substring(7) // Убираем '/api/v1'
          : presign.url.startsWith('/')
          ? presign.url.substring(1) // Убираем ведущий '/'
          : presign.url
        
        try {
          await http.put(uploadUrl, file, {
            headers: {
              ...presign.headers,
              'Content-Type': presign.headers?.['Content-Type'] || 'application/octet-stream',
            },
            timeout: 60000, // 60 секунд для больших файлов
          })
        } catch (uploadErr: any) {
          // Обработка ошибки 413 (Content Too Large)
          if (uploadErr?.response?.status === 413) {
            throw new Error(`Файл "${file.name}" слишком большой. Максимальный размер: 20 МБ.`)
          }
          throw new Error(uploadErr?.response?.data?.detail || uploadErr?.message || `Ошибка загрузки файла: ${uploadErr?.response?.status || 'unknown'}`)
        }
        
        // Сообщаем бэкенду о загрузке
        const formData = new FormData()
        formData.append('doc_type', docType)
        formData.append('storage_key', presign.key)
        await uploadPublicDocument(token, formData)
      }
      
      // Обновляем состояние после успешной загрузки
      await refresh()
      
      // ВАЖНО: Обновляем локальное состояние документа на 'uploaded' ПОСЛЕ refresh
      // Это гарантирует, что статус будет установлен даже если refresh не обновил documents
      setDocuments(prev => ({
        ...prev,
        [docType]: { type: docType, status: 'uploaded', files: files }
      }))
      
      // Очищаем ошибки
      setDocUploadErrors(prev => ({ ...prev, [docType]: null }))
      setError(null)
    } catch (err: any) {
      let errorMessage: string
      if (err?.response?.status === 413 || err?.message?.includes('413') || err?.message?.includes('too large') || err?.message?.includes('Content Too Large')) {
        errorMessage = `Файл "${files[0]?.name || ''}" слишком большой. Максимальный размер: 20 МБ.`
      } else {
        errorMessage = err?.response?.data?.detail || err?.message || t('public.intake.new.errors.upload_failed')
      }
      setDocUploadErrors(prev => ({ ...prev, [docType]: errorMessage }))
      setError(errorMessage)
      
      // Сбрасываем статус документа на "в процессе" при ошибке, чтобы пользователь мог выбрать другой вариант
      setDocuments(prev => ({
        ...prev,
        [docType]: { type: docType, status: 'in_progress', files: [] }
      }))
    } finally {
      setDocUploading(prev => ({ ...prev, [docType]: false }))
    }
  }, [token, refresh, t])
  
  // Оптимизированное автосохранение - используем useRef для хранения последних значений
  const contactsRef = useRef(contacts)
  const answersRef = useRef(answers)
  const employmentsRef = useRef(employments)
  
  useEffect(() => {
    contactsRef.current = contacts
    answersRef.current = answers
    employmentsRef.current = employments
  }, [contacts, answers, employments])
  
  // Автосохранение - используем отдельный useEffect для каждого изменения
  useEffect(() => {
    if (!token) return
    if (currentStep === 'language' || currentStep === 'thank_you' || currentStep === 'overview') return
    if (apiLoading) return
    
    // Очищаем предыдущий таймер
    if (saveDebounceTimer.current) {
      window.clearTimeout(saveDebounceTimer.current)
    }
    
    // Устанавливаем новый таймер для автосохранения
    saveDebounceTimer.current = window.setTimeout(() => {
      try {
        // Используем refs для получения актуальных значений
        const currentAnswers = answersRef.current
        const currentContacts = contactsRef.current
        const currentEmployments = employmentsRef.current
        
        // Собираем данные напрямую без вызова buildIntakeData
        const locationAnswer = currentAnswers.find(a => a.questionId === 'location')
        const citizenshipAnswer = currentAnswers.find(a => a.questionId === 'citizenship')
        const stayBasisAnswer = currentAnswers.find(a => a.questionId === 'stay_basis')
        const ceExperienceAnswer = currentAnswers.find(a => a.questionId === 'ce_experience')
        const trailerTypesAnswer = currentAnswers.find(a => a.questionId === 'trailer_types')
        const frigoAnswer = currentAnswers.find(a => a.questionId === 'frigo_experience')
        const intlAnswer = currentAnswers.find(a => a.questionId === 'intl_experience')
        const hasAdrAnswer = currentAnswers.find(a => a.questionId === 'has_adr')
        const birthDateAnswer = currentAnswers.find(a => a.questionId === 'birth_date')
        
        // Преобразуем опыт CE
        let yearsCe: number | null = null
        if (ceExperienceAnswer) {
          const value = ceExperienceAnswer.value
          if (typeof value === 'number') {
            yearsCe = Math.round(value)
          } else if (typeof value === 'string') {
            if (value === '0') yearsCe = 0
            else if (value === '1-2') yearsCe = 2
            else if (value === '3-5') yearsCe = 4
            else if (value === '5-10') yearsCe = 8
            else if (value === '10+') yearsCe = 10
            else {
              const parsed = parseFloat(value)
              if (!isNaN(parsed)) yearsCe = Math.round(parsed)
            }
          }
        }
        
        // Валидация citizenship
        let citizenship: string | null = null
        if (citizenshipAnswer?.value) {
          const str = typeof citizenshipAnswer.value === 'string' ? citizenshipAnswer.value.trim().toUpperCase() : String(citizenshipAnswer.value).trim().toUpperCase()
          citizenship = str.length === 2 ? str : null
        }
        if (citizenship && citizenship.length !== 2) {
          return
        }
        
        // Валидация employments
        const validEmployments = currentEmployments
          .filter(emp => emp.employer_name && emp.employer_name.trim())
          .map(emp => {
            let countryValue: string | null = null
            if (emp.country) {
              const countryStr = typeof emp.country === 'string' ? emp.country.trim().toUpperCase() : String(emp.country).trim().toUpperCase()
              countryValue = countryStr.length === 2 ? countryStr : null
            }
            return {
              employer_name: emp.employer_name.trim(),
              country: countryValue,
              position: emp.position?.trim() || null,
              start_date: typeof emp.start_date === 'string' ? emp.start_date : (emp.start_date ? String(emp.start_date) : new Date().toISOString().split('T')[0]),
              end_date: emp.currently_employed ? null : (emp.end_date ? (typeof emp.end_date === 'string' ? emp.end_date : String(emp.end_date)) : null),
              trailer_types: [],
              route_types: [],
            }
          })
          .filter(emp => {
            if (!emp.employer_name || !emp.employer_name.trim()) return false
            if (emp.country && emp.country.length !== 2) return false
            return true
          })
        
        const fullName = `${currentContacts.first_name} ${currentContacts.last_name}`.trim()
        
        const finalData: IntakeData = {
          contacts: {
            phone_country_code: currentContacts.phone_country_code?.trim() || null,
            phone: currentContacts.phone?.trim() || null,
            email: currentContacts.email?.trim() || null,
            preferred_messenger: 'whatsapp',
          },
          personal: {
            full_name: fullName || null,
            citizenship,
            residency_status: stayBasisAnswer?.value ? (typeof stayBasisAnswer.value === 'string' ? stayBasisAnswer.value.trim() : String(stayBasisAnswer.value).trim()) : null,
            in_poland: locationAnswer?.value === 'in_poland' ? true : locationAnswer?.value === 'not_in_poland' ? false : null,
            birth_date: birthDateAnswer?.value ? (typeof birthDateAnswer.value === 'string' ? birthDateAnswer.value.trim() : (birthDateAnswer.value instanceof Date ? birthDateAnswer.value.toISOString().split('T')[0] : String(birthDateAnswer.value).trim())) : null,
            current_location: locationAnswer?.value ? (locationAnswer.value === 'in_poland' ? 'in_poland' : locationAnswer.value === 'not_in_poland' ? 'not_in_poland' : locationAnswer.value === 'other' ? 'other' : String(locationAnswer.value)) : null,
            frigo_experience: frigoAnswer?.value === 'yes' ? true : frigoAnswer?.value === 'no' ? false : null,
            has_adr: hasAdrAnswer?.value === 'yes' ? true : hasAdrAnswer?.value === 'no' ? false : null,
          },
          experience: {
            years_ce: yearsCe !== null ? Math.round(yearsCe) : null,
            intl_experience: intlAnswer?.value === true || intlAnswer?.value === 'yes' ? true : (intlAnswer?.value === false || intlAnswer?.value === 'no' ? false : null),
            trailer_types: Array.isArray(trailerTypesAnswer?.value) ? trailerTypesAnswer.value.filter((v): v is string => typeof v === 'string') : [],
            route_types: [],
          },
          employments: validEmployments,
          agreements: {
            general: false,
            employer_share: false,
            terms_acceptance: false,
            cookies_accepted: isCookieConsentGranted(),
          },
        }
        
        // Используем прямой вызов API
        updatePublicIntake(token, finalData).catch(() => {
          // Тихая ошибка
        })
      } catch (error) {
        // Тихая ошибка
      }
    }, 1500)
    
    return () => {
      if (saveDebounceTimer.current) {
        window.clearTimeout(saveDebounceTimer.current)
      }
    }
  }, [contacts, answers, employments, currentStep, token, apiLoading, updatePublicIntake])

  const handleLanguageSelect = (lang: 'ru' | 'en' | 'pl') => {
    setLocale(lang)
    localStorage.setItem('intake_locale', lang)
    setCurrentStep('contacts')
  }

  const handleContactsSubmit = async () => {
    // Валидация
    if (!contacts.first_name.trim() || !contacts.last_name.trim()) {
      setError(t('public.intake.new.errors.name_required'))
      return
    }
    if (!contacts.phone.trim() && !contacts.email.trim()) {
      setError(t('public.intake.new.errors.contact_required'))
      return
    }
    setError(null)
    
    // Сохраняем контакты через API
    apiUpdateContacts({
      phone_country_code: contacts.phone_country_code || null,
      phone: contacts.phone || null,
      email: contacts.email || null,
    })
    apiUpdatePersonal({
      full_name: `${contacts.first_name} ${contacts.last_name}`.trim(),
    })
    
    setCurrentStep('questions')
    setCurrentQuestionIndex(0)
  }

  const handleQuestionAnswer = (value: any) => {
    const question = questions[currentQuestionIndex]
    const newAnswers = [...answers]
    const existingIndex = newAnswers.findIndex(a => a.questionId === question.id)
    
    if (existingIndex >= 0) {
      newAnswers[existingIndex] = { questionId: question.id, value }
    } else {
      newAnswers.push({ questionId: question.id, value })
    }
    
    setAnswers(newAnswers)
    
    // Синхронизируем с API
    if (question.id === 'citizenship') {
      // Бэкенд требует ровно 2 символа для кода страны
      const citizenshipValue = value ? (typeof value === 'string' ? value.trim().toUpperCase() : String(value).trim().toUpperCase()) : null
      apiUpdatePersonal({ citizenship: citizenshipValue && citizenshipValue.length === 2 ? citizenshipValue : null })
    } else if (question.id === 'stay_basis') {
      const residencyValue = value ? (typeof value === 'string' ? value.trim() : String(value).trim()) : null
      apiUpdatePersonal({ residency_status: residencyValue })
    } else if (question.id === 'location') {
      const inPoland = value === 'in_poland' ? true : value === 'not_in_poland' ? false : null
      const currentLocation = value === 'in_poland' ? 'in_poland' 
        : value === 'not_in_poland' ? 'not_in_poland'
        : value === 'other' ? 'other'
        : value ? String(value) : null
      apiUpdatePersonal({ in_poland: inPoland, current_location: currentLocation })
    } else if (question.id === 'ce_experience') {
      let yearsCe: number | null = null
      if (typeof value === 'number') {
        yearsCe = Math.round(value) // Округляем до целого
      } else if (typeof value === 'string') {
        if (value === '0') yearsCe = 0
        else if (value === '1-2') yearsCe = 2 // Округляем до целого (берем верхнюю границу)
        else if (value === '3-5') yearsCe = 4
        else if (value === '5-10') yearsCe = 8 // Округляем до целого (берем верхнюю границу)
        else if (value === '10+') yearsCe = 10
        else {
          const parsed = parseFloat(value)
          if (!isNaN(parsed)) yearsCe = Math.round(parsed) // Округляем до целого
        }
      }
      apiUpdateExperience((current) => ({ ...current, years_ce: yearsCe }))
    } else if (question.id === 'trailer_types') {
      // ВАЖНО: trailer_types должен быть массивом строк
      const trailerTypes = Array.isArray(value) 
        ? value.filter((v): v is string => typeof v === 'string')
        : []
      apiUpdateExperience((current) => ({ 
        ...current, 
        trailer_types: trailerTypes
      }))
    } else if (question.id === 'intl_experience') {
      const intlValue = value === true || value === 'yes' ? true : value === false || value === 'no' ? false : null
      apiUpdateExperience((current) => ({ 
        ...current, 
        intl_experience: intlValue
      }))
    } else if (question.id === 'frigo_experience') {
      const frigoValue = value === true || value === 'yes' ? true : value === false || value === 'no' ? false : null
      apiUpdatePersonal({ frigo_experience: frigoValue })
    } else if (question.id === 'has_adr') {
      const adrValue = value === true || value === 'yes' ? true : value === false || value === 'no' ? false : null
      // ВАЖНО: Устанавливаем локальное состояние hasAdr для правильной работы логики документов
      setHasAdr(adrValue)
      apiUpdatePersonal({ has_adr: adrValue })
    } else if (question.id === 'birth_date') {
      let birthDateValue: string | null = null
      if (value) {
        if (typeof value === 'string') {
          birthDateValue = value.trim()
        } else if (value instanceof Date) {
          birthDateValue = value.toISOString().split('T')[0]
        } else {
          birthDateValue = String(value).trim()
        }
      }
      apiUpdatePersonal({ birth_date: birthDateValue })
    }
  }

  const handleQuestionNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
    } else {
      setCurrentStep('employment')
    }
  }

  const handleQuestionBack = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1)
    } else {
      setCurrentStep('contacts')
    }
  }

  // Если нет токена, редиректим (ПОСЛЕ всех хуков и обработчиков!)
  if (!token) {
    return <Navigate to="/public/intake" replace />
  }

  const isTokenExpired = !apiLoading && apiError && !apiState
  const intakeHeaderSub = ['contacts', 'questions', 'employment', 'documents', 'review'].includes(currentStep) ? (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <IntakeProgressBar
        currentStep={currentStep}
        timeEstimate={['contacts', 'questions'].includes(currentStep) ? t('public.intake.new.progress.time_estimate', { defaultValue: '~15–20 min' }) : undefined}
      />
      <AutosaveIndicator saving={apiSaving} />
    </div>
  ) : undefined

  // Истёк срок ссылки или ошибка загрузки
  if (isTokenExpired) {
    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />}>
        <div className="rounded-3xl border border-amber-200 bg-amber-50 p-8 shadow-card text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h1 className="text-xl font-semibold text-slate-900 mb-2">
            {t('public.intake.new.errors.token_expired', { defaultValue: 'Link expired or invalid' })}
          </h1>
          <p className="text-slate-600 mb-6">
            {t('public.intake.new.errors.token_expired_hint', {
              defaultValue: 'Request a new link to continue your application.',
            })}
          </p>
          <Link
            to="/public/intake"
            className="inline-flex rounded-xl bg-brand-600 px-6 py-3 text-white font-semibold hover:bg-brand-700"
          >
            {t('public.intake.new.errors.request_new_link', { defaultValue: 'Get new link' })}
          </Link>
        </div>
      </PublicPageShell>
    )
  }

  // Показываем загрузку при первой загрузке данных
  if (apiLoading && !dataRestored) {
    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />}>
        <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600 mx-auto mb-4"></div>
          <p className="text-slate-600">{t('public.intake.new.loading')}</p>
        </div>
      </PublicPageShell>
    )
  }

  // Рендер шага выбора языка
  if (currentStep === 'language') {
    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl">
        <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card text-center">
          <PublicLogo showWordmark className="mx-auto mb-6" />
          <h1 className="text-2xl font-semibold text-slate-900 mb-4">
            {t('public.intake.new.language.title')}
          </h1>
          <p className="text-slate-600 mb-2">
            {t('public.intake.new.language.subtitle')}
          </p>
          <p className="text-sm text-slate-500 mb-8">
            {t('public.intake.new.progress.time_estimate', { defaultValue: '~15–20 min' })}
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <button
              onClick={() => handleLanguageSelect('ru')}
              className="rounded-xl border-2 border-brand-200 bg-white px-8 py-4 text-lg font-semibold text-brand-700 hover:border-brand-400 hover:bg-brand-50 transition"
            >
              Русский
            </button>
            <button
              onClick={() => handleLanguageSelect('en')}
              className="rounded-xl border-2 border-brand-200 bg-white px-8 py-4 text-lg font-semibold text-brand-700 hover:border-brand-400 hover:bg-brand-50 transition"
            >
              English
            </button>
            <button
              onClick={() => handleLanguageSelect('pl')}
              className="rounded-xl border-2 border-brand-200 bg-white px-8 py-4 text-lg font-semibold text-brand-700 hover:border-brand-400 hover:bg-brand-50 transition"
            >
              Polski
            </button>
          </div>
        </div>
      </PublicPageShell>
    )
  }

  // Рендер шага контактов
  if (currentStep === 'contacts') {
    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />} headerSub={intakeHeaderSub}>
        <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card">
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-2xl font-semibold text-slate-900">
                {t('public.intake.new.step1.title')}
              </h1>
              <span className="text-sm text-slate-500">
                {t('public.intake.new.progress.step', { values: { current: 1, total: 6 } })}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span className="text-sm text-slate-600">{t('public.intake.new.progress.checkpoint.personal_data')}</span>
            </div>
          </div>

          <form onSubmit={(e) => { e.preventDefault(); handleContactsSubmit(); }} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {t('public.intake.new.step1.first_name')} *
                </label>
                <input
                  type="text"
                  value={contacts.first_name}
                  onChange={(e) => setContacts({ ...contacts, first_name: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {t('public.intake.new.step1.last_name')} *
                </label>
                <input
                  type="text"
                  value={contacts.last_name}
                  onChange={(e) => setContacts({ ...contacts, last_name: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                  required
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-[140px_1fr]">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {t('public.intake.new.step1.country_code')}
                </label>
                <input
                  type="text"
                  value={contacts.phone_country_code}
                  onChange={(e) => setContacts({ ...contacts, phone_country_code: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                  placeholder="+48"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {t('public.intake.new.step1.phone')} *
                </label>
                <input
                  type="tel"
                  value={contacts.phone}
                  onChange={(e) => setContacts({ ...contacts, phone: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                  required={!contacts.email}
                />
                <p className="mt-1 text-xs text-slate-500">
                  {t('public.intake.new.step1.phone_hint')}
                </p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('public.intake.new.step1.email')} *
              </label>
              <input
                type="email"
                value={contacts.email}
                onChange={(e) => setContacts({ ...contacts, email: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                required={!contacts.phone}
              />
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="w-full rounded-lg bg-brand-600 px-4 py-3 text-white font-semibold shadow-sm transition hover:bg-brand-700"
            >
              {t('public.intake.new.cta.continue')}
            </button>
          </form>
        </div>
      </PublicPageShell>
    )
  }


  // Рендер шага вопросов
  if (currentStep === 'questions') {
    const question = questions[currentQuestionIndex]
    const currentAnswer = getCurrentAnswer()
    const canProceed = currentAnswer !== undefined && currentAnswer !== null && currentAnswer !== ''

    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />} headerSub={intakeHeaderSub}>
        <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card">
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-2xl font-semibold text-slate-900">
                {t(`public.intake.new.questions.${question.id}.title`)}
              </h1>
              <span className="text-sm text-slate-500">
                {t('public.intake.new.progress.question', { 
                  values: { current: currentQuestionIndex + 1, total: questions.length } 
                })}
              </span>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span className="text-sm text-slate-600">
                {t('public.intake.new.progress.checkpoint.questions')}
              </span>
            </div>
          </div>

          <div className="space-y-4">
            {/* Рендер вопроса в зависимости от типа */}
            {question.type === 'select' && question.id === 'location' && (
              <div className="space-y-3">
                {locationOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleQuestionAnswer(option.value)}
                    className={`w-full rounded-lg border-2 px-4 py-3 text-left transition ${
                      currentAnswer === option.value
                        ? 'border-brand-500 bg-brand-50 text-brand-900'
                        : 'border-slate-200 bg-white text-slate-700 hover:border-brand-300'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}

            {question.type === 'select' && question.id === 'citizenship' && (
              <Select
                options={countryOptions}
                value={currentAnswer || ''}
                onChange={(value) => handleQuestionAnswer(value)}
                placeholder={t('public.intake.new.questions.citizenship.placeholder')}
                className="w-full"
              />
            )}

            {question.type === 'select' && question.id === 'stay_basis' && (
              <div className="space-y-3">
                {stayBasisOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleQuestionAnswer(option.value)}
                    className={`w-full rounded-lg border-2 px-4 py-3 text-left transition ${
                      currentAnswer === option.value
                        ? 'border-brand-500 bg-brand-50 text-brand-900'
                        : 'border-slate-200 bg-white text-slate-700 hover:border-brand-300'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}

            {question.type === 'number' && question.id === 'ce_experience' && (
              <div className="space-y-3">
                {ceExperienceOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleQuestionAnswer(option.value)}
                    className={`w-full rounded-lg border-2 px-4 py-3 text-left transition ${
                      currentAnswer === option.value
                        ? 'border-brand-500 bg-brand-50 text-brand-900'
                        : 'border-slate-200 bg-white text-slate-700 hover:border-brand-300'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
                <div className="mt-4">
                  <input
                    type="number"
                    min="0"
                    value={typeof currentAnswer === 'string' && !ceExperienceOptions.find(o => o.value === currentAnswer) ? currentAnswer : ''}
                    onChange={(e) => handleQuestionAnswer(e.target.value)}
                    placeholder={t('public.intake.new.questions.ce_experience.custom_placeholder')}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                  />
                </div>
              </div>
            )}

            {question.type === 'multiselect' && question.id === 'trailer_types' && (
              <div className="space-y-3">
                {trailerTypeOptions.map((option) => {
                  const selected = Array.isArray(currentAnswer) && currentAnswer.includes(option.value)
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        const current = Array.isArray(currentAnswer) ? currentAnswer : []
                        const newValue = selected
                          ? current.filter(v => v !== option.value)
                          : [...current, option.value]
                        handleQuestionAnswer(newValue)
                      }}
                      className={`w-full rounded-lg border-2 px-4 py-3 text-left transition ${
                        selected
                          ? 'border-brand-500 bg-brand-50 text-brand-900'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-brand-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{option.label}</span>
                        {selected && <span className="text-brand-600">✓</span>}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}

            {(question.id === 'frigo_experience' || question.id === 'intl_experience' || question.id === 'has_adr') && (
              <div className="space-y-3">
                {yesNoOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleQuestionAnswer(option.value === 'yes')}
                    className={`w-full rounded-lg border-2 px-4 py-3 text-left transition ${
                      currentAnswer === (option.value === 'yes')
                        ? 'border-brand-500 bg-brand-50 text-brand-900'
                        : 'border-slate-200 bg-white text-slate-700 hover:border-brand-300'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}

            {question.type === 'date' && question.id === 'birth_date' && (
              <input
                type="date"
                value={currentAnswer || ''}
                onChange={(e) => handleQuestionAnswer(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                max={new Date().toISOString().split('T')[0]}
              />
            )}

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={handleQuestionBack}
                className="flex-1 rounded-lg border border-slate-300 px-4 py-3 text-slate-700 hover:bg-slate-50 transition"
              >
                {t('public.intake.new.cta.back')}
              </button>
              <button
                type="button"
                onClick={handleQuestionNext}
                disabled={!canProceed}
                className="flex-1 rounded-lg bg-brand-600 px-4 py-3 text-white font-semibold shadow-sm transition hover:bg-brand-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
              >
                {currentQuestionIndex < questions.length - 1
                  ? t('public.intake.new.cta.next')
                  : t('public.intake.new.cta.continue')}
              </button>
            </div>
          </div>
        </div>
      </PublicPageShell>
    )
  }

  const handleAddEmployment = () => {
    if (!employmentDraft.employer_name.trim() || !employmentDraft.country || !employmentDraft.start_date) {
      setError(t('public.intake.new.employment.errors.required_fields'))
      return
    }
    if (!employmentDraft.currently_employed && !employmentDraft.end_date) {
      setError(t('public.intake.new.employment.errors.end_date_required'))
      return
    }
    setError(null)
    
    const newEmployment = { ...employmentDraft }
    setEmployments([...employments, newEmployment])
    
    // Сохраняем через API
    const index = employments.length
    // Валидация country - должен быть ровно 2 символа или null
    let countryValue: string | null = null
    if (newEmployment.country) {
      const countryStr = typeof newEmployment.country === 'string' ? newEmployment.country.trim().toUpperCase() : String(newEmployment.country).trim().toUpperCase()
      countryValue = countryStr.length === 2 ? countryStr : null
    }
    
    apiUpsertEmployment(index, {
      employer_name: newEmployment.employer_name.trim(),
      country: countryValue,
      position: newEmployment.position?.trim() || null,
      // ВАЖНО: start_date и end_date должны быть строками в формате 'YYYY-MM-DD'
      start_date: typeof newEmployment.start_date === 'string' ? newEmployment.start_date : (newEmployment.start_date ? String(newEmployment.start_date) : new Date().toISOString().split('T')[0]),
      end_date: newEmployment.currently_employed ? null : (newEmployment.end_date ? (typeof newEmployment.end_date === 'string' ? newEmployment.end_date : String(newEmployment.end_date)) : null),
      // Бэкенд ожидает эти поля, но они опциональны
      trailer_types: [],
      route_types: [],
    })
    
    setEmploymentDraft({
      employer_name: '',
      country: '',
      position: '',
      start_date: new Date().toISOString().split('T')[0],
      end_date: null,
      currently_employed: false,
    })
  }

  const handleRemoveEmployment = (index: number) => {
    setEmployments(employments.filter((_, i) => i !== index))
    apiRemoveEmployment(index)
  }

  const handleEmploymentContinue = () => {
    if (employments.length === 0) {
      // Показываем модальное окно
      const confirmed = window.confirm(t('public.intake.new.employment.skip_warning'))
      if (!confirmed) return
    }
    setCurrentStep('documents')
  }

  // Рендер шага опыта работы
  if (currentStep === 'employment') {
    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />} headerSub={intakeHeaderSub}>
        <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card">
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-2xl font-semibold text-slate-900">
                {t('public.intake.new.employment.title')}
              </h1>
              <span className="text-sm text-slate-500">
                {t('public.intake.new.progress.step', { values: { current: 3, total: 6 } })}
              </span>
            </div>
            <p className="text-slate-600 mt-2">
              {t('public.intake.new.employment.subtitle')}
            </p>
            <div className="mt-4 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span className="text-sm text-slate-600">
                {t('public.intake.new.progress.checkpoint.employment')}
              </span>
            </div>
          </div>

          <div className="space-y-4">
            {/* Список добавленных работодателей */}
            {employments.length > 0 && (
              <div className="space-y-3">
                {employments.map((emp, index) => (
                  <div key={index} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-semibold text-slate-900">{emp.employer_name}</p>
                        <p className="text-sm text-slate-600">
                          {emp.position || t('public.intake.new.employment.driver')} · {emp.country} · {emp.start_date} → {emp.currently_employed ? t('public.intake.new.employment.current') : emp.end_date}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveEmployment(index)}
                        className="text-sm text-red-600 hover:text-red-700"
                      >
                        {t('common.actions.delete')}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Форма добавления работодателя */}
            <div className="rounded-lg border border-brand-200 bg-brand-50/30 p-6 space-y-4">
              <h3 className="font-semibold text-slate-900">
                {t('public.intake.new.employment.add_title')}
              </h3>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {t('public.intake.new.employment.company')} *
                  </label>
                  <input
                    type="text"
                    value={employmentDraft.employer_name}
                    onChange={(e) => setEmploymentDraft({ ...employmentDraft, employer_name: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {t('public.intake.new.employment.country')} *
                  </label>
                  <Select
                    options={countryOptions}
                    value={employmentDraft.country}
                    onChange={(value) => setEmploymentDraft({ ...employmentDraft, country: value || '' })}
                    placeholder={t('public.intake.new.employment.country_placeholder')}
                    className="w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {t('public.intake.new.employment.position')}
                </label>
                <input
                  type="text"
                  value={employmentDraft.position}
                  onChange={(e) => setEmploymentDraft({ ...employmentDraft, position: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                  placeholder={t('public.intake.new.employment.position_placeholder')}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {t('public.intake.new.employment.start_date')} *
                  </label>
                  <input
                    type="date"
                    value={employmentDraft.start_date}
                    onChange={(e) => setEmploymentDraft({ ...employmentDraft, start_date: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {t('public.intake.new.employment.end_date')} {!employmentDraft.currently_employed && '*'}
                  </label>
                  <input
                    type="date"
                    value={employmentDraft.end_date || ''}
                    onChange={(e) => setEmploymentDraft({ ...employmentDraft, end_date: e.target.value || null })}
                    disabled={employmentDraft.currently_employed}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 disabled:bg-slate-100 disabled:cursor-not-allowed"
                    required={!employmentDraft.currently_employed}
                  />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="currently_employed"
                  checked={employmentDraft.currently_employed}
                  onChange={(e) => setEmploymentDraft({ 
                    ...employmentDraft, 
                    currently_employed: e.target.checked,
                    end_date: e.target.checked ? null : employmentDraft.end_date
                  })}
                  className="h-4 w-4 accent-brand-600"
                />
                <label htmlFor="currently_employed" className="text-sm text-slate-700">
                  {t('public.intake.new.employment.currently_employed')}
                </label>
              </div>

              <button
                type="button"
                onClick={handleAddEmployment}
                className="w-full rounded-lg bg-brand-600 px-4 py-2 text-white font-semibold shadow-sm transition hover:bg-brand-700"
              >
                {t('public.intake.new.employment.add')}
              </button>
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">
                {error}
              </div>
            )}

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => setCurrentStep('questions')}
                className="flex-1 rounded-lg border border-slate-300 px-4 py-3 text-slate-700 hover:bg-slate-50 transition"
              >
                {t('public.intake.new.cta.back')}
              </button>
              <button
                type="button"
                onClick={handleEmploymentContinue}
                className="flex-1 rounded-lg bg-brand-600 px-4 py-3 text-white font-semibold shadow-sm transition hover:bg-brand-700"
              >
                {t('public.intake.new.cta.continue')}
              </button>
            </div>
          </div>
        </div>
      </PublicPageShell>
    )
  }


  const handleDocumentStatus = async (status: DocumentStatus, files?: File[]) => {
    const doc = getCurrentDocument()
    if (!doc) return
    
    // Устанавливаем статус в локальном состоянии
    setDocuments(prev => ({
      ...prev,
      [doc.type]: { type: doc.type, status, files: files || [] }
    }))
    
    // Если статус "загрузить" и есть файлы - загружаем
    if (status === 'uploaded' && files && files.length > 0 && token) {
      try {
        await uploadDocumentFiles(doc.type, files)
        // После успешной загрузки статус уже установлен в 'uploaded' в uploadDocumentFiles
        // Но убеждаемся, что он остался 'uploaded'
        setDocuments(prev => ({
          ...prev,
          [doc.type]: { type: doc.type, status: 'uploaded', files: files }
        }))
      } catch (error) {
        // При ошибке загрузки сбрасываем статус на 'in_progress', чтобы пользователь мог выбрать другой вариант
        setDocuments(prev => ({
          ...prev,
          [doc.type]: { type: doc.type, status: 'in_progress', files: [] }
        }))
        throw error // Пробрасываем ошибку дальше
      }
    }
  }

  // Все обработчики объявлены до условных возвратов
  const handleDocumentNext = () => {
    const doc = getCurrentDocument()
    if (!doc) {
      // Если нет документа - проверяем, может быть нужно показать вопрос об ADR
      if (currentDocumentIndex >= documentFlow.length && hasAdr === null) {
        // Остаемся на том же месте, покажем вопрос об ADR
        return
      }
      // Иначе переходим к обзору
      setCurrentStep('review')
      return
    }
    
    // Проверяем обязательность
    const docEntry = documents[doc.type]
    
    // ВАЖНО: Для обязательных документов разрешаем переход только если:
    // - документ загружен (uploaded) ИЛИ
    // - документ в процессе оформления (in_progress)
    // НЕ разрешаем переход если статус 'missing' или нет статуса
    if (doc.required) {
      if (!docEntry) {
        setError(t('public.intake.new.documents.errors.required_missing'))
        return
      }
      if (docEntry.status === 'missing') {
        setError(t('public.intake.new.documents.errors.required_missing'))
        return
      }
      // Если документ обязательный, но не загружен и не в процессе - не разрешаем переход
      if (docEntry.status !== 'uploaded' && docEntry.status !== 'in_progress') {
        setError(t('public.intake.new.documents.errors.required_missing'))
        return
      }
    }
    
    // Если документ не обязательный или статус корректный - очищаем ошибки и продолжаем
    setError(null)
    
    // ВАЖНО: Проверяем, это последний документ в flow?
    const isLastDocument = currentDocumentIndex >= documentFlow.length - 1
    
    if (isLastDocument) {
      // Это последний документ - проверяем ADR
      if (hasAdr === null) {
        // ADR еще не задан - остаемся здесь, покажем вопрос об ADR
        // Но сначала увеличиваем индекс, чтобы getCurrentDocument вернул null
        setCurrentDocumentIndex(currentDocumentIndex + 1)
        return
      }
      // ADR уже задан или не нужен - переходим к обзору
      setCurrentStep('review')
    } else {
      // Не последний документ - переходим к следующему
      setCurrentDocumentIndex(currentDocumentIndex + 1)
    }
  }

  // Рендер шага документов
  if (currentStep === 'documents') {
    // Вопрос о правах с 95 кодом
    if (hasLicenseWith95 === null) {
      return (
        <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />} headerSub={intakeHeaderSub}>
          <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card">
            <div className="mb-6">
              <h1 className="text-2xl font-semibold text-slate-900 mb-2">
                {t('public.intake.new.documents.license_question')}
              </h1>
              <span className="text-sm text-slate-500">
                {t('public.intake.new.progress.step', { values: { current: 4, total: 6 } })}
              </span>
            </div>

            <div className="space-y-3 mb-6">
              {yesNoOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    setHasLicenseWith95(option.value === 'yes')
                    setCurrentDocumentIndex(0) // начинаем с первого документа в flow
                  }}
                  className="w-full rounded-lg border-2 px-4 py-3 text-left transition border-slate-200 bg-white text-slate-700 hover:border-brand-300"
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </PublicPageShell>
      )
    }

    // Вопрос об ADR (когда дошли до конца обязательных документов)
    if (currentDocumentIndex >= documentFlow.length && hasAdr === null) {
      return (
        <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />} headerSub={intakeHeaderSub}>
          <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card">
            <div className="mb-6">
              <h1 className="text-2xl font-semibold text-slate-900 mb-2">
                {t('public.intake.new.documents.adr_question')}
              </h1>
            </div>

            <div className="space-y-3 mb-6">
              {yesNoOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    setHasAdr(option.value === 'yes')
                    if (option.value === 'no') {
                      setCurrentStep('review') // пропускаем ADR, переходим к обзору
                    } else {
                      // Добавляем ADR в flow и переходим к нему
                      setCurrentDocumentIndex(documentFlow.length)
                    }
                  }}
                  className="w-full rounded-lg border-2 px-4 py-3 text-left transition border-slate-200 bg-white text-slate-700 hover:border-brand-300"
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </PublicPageShell>
      )
    }

    const doc = getCurrentDocument()
    
    if (!doc) {
      // Если нет документа, но мы в процессе - значит все документы обработаны
      if (hasLicenseWith95 !== null) {
        setCurrentStep('review')
      }
      return null
    }

    const currentDocEntry = documents[doc.type]
    const docStatus = currentDocEntry?.status

    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />} headerSub={intakeHeaderSub}>
        <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card">
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-2xl font-semibold text-slate-900">
                {t(`public.intake.new.documents.${doc.type}.title`)}
              </h1>
              <span className="text-sm text-slate-500">
                {documentFlow.length > 0 && t('public.intake.new.progress.document', { 
                  values: { current: currentDocumentIndex + 1, total: documentFlow.length } 
                })}
              </span>
            </div>
            {doc.required && (
              <p className="text-sm text-rose-600 mt-1">
                {t('public.intake.new.documents.required')}
              </p>
            )}
          </div>

          <div className="space-y-4">
            {/* Три варианта статуса */}
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => handleDocumentStatus('uploaded')}
                className={`w-full rounded-lg border-2 px-4 py-3 text-left transition ${
                  docStatus === 'uploaded'
                    ? 'border-brand-500 bg-brand-50 text-brand-900'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-brand-300'
                }`}
              >
                {t('public.intake.new.documents.status.upload')}
              </button>
              <button
                type="button"
                onClick={() => handleDocumentStatus('in_progress')}
                className={`w-full rounded-lg border-2 px-4 py-3 text-left transition ${
                  docStatus === 'in_progress'
                    ? 'border-amber-500 bg-amber-50 text-amber-900'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-amber-300'
                }`}
              >
                {t('public.intake.new.documents.status.in_progress')}
              </button>
              {!doc.required && (
                <button
                  type="button"
                  onClick={() => handleDocumentStatus('missing')}
                  className={`w-full rounded-lg border-2 px-4 py-3 text-left transition ${
                    docStatus === 'missing'
                      ? 'border-slate-500 bg-slate-50 text-slate-900'
                      : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                  }`}
                >
                  {t('public.intake.new.documents.status.missing')}
                </button>
              )}
            </div>

            {/* Поле загрузки если выбрано "Загрузить" */}
            {docStatus === 'uploaded' && (
              <div className="rounded-lg border border-dashed border-brand-200 bg-brand-50/30 p-4">
                <input
                  type="file"
                  multiple
                  accept="image/*,.pdf"
                  onChange={async (e) => {
                    const files = Array.from(e.target.files || [])
                    if (files.length > 0) {
                      await handleDocumentStatus('uploaded', files)
                    }
                  }}
                  className="w-full text-sm"
                  disabled={docUploading[doc.type]}
                />
                <p className="text-xs text-slate-500 mt-2">
                  {t('public.intake.new.documents.upload_hint')}
                </p>
                {docUploading[doc.type] && (
                  <p className="text-xs text-brand-600 mt-2">
                    {t('public.intake.new.documents.uploading')}
                  </p>
                )}
                {docUploadErrors[doc.type] && (
                  <p className="text-xs text-red-600 mt-2">
                    {docUploadErrors[doc.type]}
                  </p>
                )}
              </div>
            )}

            {error && (
              <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">
                {error}
              </div>
            )}

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => {
                  if (currentDocumentIndex > 0) {
                    setCurrentDocumentIndex(currentDocumentIndex - 1)
                  } else {
                    setCurrentStep('employment')
                  }
                }}
                className="flex-1 rounded-lg border border-slate-300 px-4 py-3 text-slate-700 hover:bg-slate-50 transition"
              >
                {t('public.intake.new.cta.back')}
              </button>
              <button
                type="button"
                onClick={handleDocumentNext}
                disabled={
                  docUploading[doc.type] || 
                  (doc.required && (!currentDocEntry || (currentDocEntry.status !== 'uploaded' && currentDocEntry.status !== 'in_progress')))
                }
                className="flex-1 rounded-lg bg-brand-600 px-4 py-3 text-white font-semibold shadow-sm transition hover:bg-brand-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
              >
                {currentDocumentIndex < documentFlow.length - 1
                  ? t('public.intake.new.cta.next')
                  : t('public.intake.new.cta.continue')}
              </button>
            </div>
          </div>
        </div>
      </PublicPageShell>
    )
  }

  // Рендер финального обзора
  if (currentStep === 'review') {
    // Уже отправлено — показываем thank_you
    if (apiState?.status === 'submitted') {
      const statusTokenSubmitted = apiState?.status_share_token || token
      const statusUrlSubmitted = statusTokenSubmitted ? `${typeof window !== 'undefined' ? window.location.origin : ''}/public/status/${statusTokenSubmitted}` : ''
      return (
        <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />}>
          <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card text-center">
            <div className="text-6xl mb-4">✅</div>
            <h1 className="text-2xl font-semibold text-slate-900 mb-2">
              {t('public.intake.new.thank_you.title')}
            </h1>
            <p className="text-slate-600 mb-6">
              {t('public.intake.new.thank_you.message')}
            </p>
            {statusUrlSubmitted && (
              <div className="mb-6 rounded-xl border border-brand-200 bg-brand-50/50 p-4 text-left">
                <p className="text-sm font-medium text-slate-700 mb-2">{t('public.intake.new.thank_you.track_status', { defaultValue: 'Śledź status swojej zgłoszenia' })}</p>
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-4">
                  <div className="flex flex-col items-center gap-1">
                    <QrCodeCanvas value={statusUrlSubmitted} size={120} className="rounded-lg" />
                    <p className="text-xs text-slate-500">{t('public.intake.new.thank_you.qr_hint', { defaultValue: 'Zeskanuj, aby dodać link na telefon' })}</p>
                  </div>
                  <div className="flex flex-col gap-2">
                    <Link
                      to={`/public/status/${statusTokenSubmitted}`}
                      className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
                    >
                      {t('public.intake.new.thank_you.open_status', { defaultValue: 'Otwórz stronę statusu' })}
                    </Link>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard?.writeText(statusUrlSubmitted).then(() => {
                          notify({ title: t('public.intake.new.thank_you.link_copied', { defaultValue: 'Link skopiowany' }), variant: 'success' })
                        }).catch(() => {})
                      }}
                      className="inline-flex items-center justify-center rounded-lg border border-brand-200 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
                    >
                      {t('public.intake.new.thank_you.copy_link', { defaultValue: 'Skopiuj link' })}
                    </button>
                  </div>
                </div>
              </div>
            )}
            <div className="mb-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left">
              <p className="text-sm font-medium text-slate-700 mb-2">
                {t('public.intake.new.thank_you.telegram_title', { defaultValue: 'Telegram assistant' })}
              </p>
              <p className="text-sm text-slate-600 mb-3">
                {t('public.intake.new.thank_you.telegram_hint', { defaultValue: 'Open bot and send your email or phone number to link your profile and track status updates.' })}
              </p>
              <a
                href={telegramBotUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                {t('public.intake.new.thank_you.telegram_open', { defaultValue: 'Open Telegram bot' })}
              </a>
            </div>
            <button
              type="button"
              onClick={() => setCurrentStep('overview')}
              className="rounded-lg bg-brand-600 px-6 py-3 text-white font-semibold shadow-sm transition hover:bg-brand-700"
            >
              {t('public.intake.new.thank_you.go_to_overview')}
            </button>
          </div>
        </PublicPageShell>
      )
    }
    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="5xl" headerExtra={<PublicLocaleSwitcher />} headerSub={intakeHeaderSub}>
        <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-slate-900 mb-2">
              {t('public.intake.new.review.title')}
            </h1>
            <p className="text-slate-600">
              {t('public.intake.new.review.subtitle')}
            </p>
          </div>

          <div className="space-y-4">
            {/* Блок личных данных */}
            <div className="rounded-lg border border-slate-200 bg-white p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-900">
                  {t('public.intake.new.review.contacts')}
                </h2>
                <button
                  type="button"
                  onClick={() => setCurrentStep('contacts')}
                  className="text-sm text-brand-600 hover:text-brand-700"
                >
                  {t('public.intake.new.review.edit')}
                </button>
              </div>
              <div className="grid gap-2 text-sm">
                <p><span className="font-medium">{t('public.intake.new.step1.first_name')}:</span> {contacts.first_name}</p>
                <p><span className="font-medium">{t('public.intake.new.step1.last_name')}:</span> {contacts.last_name}</p>
                <p><span className="font-medium">{t('public.intake.new.step1.phone')}:</span> {contacts.phone_country_code} {contacts.phone}</p>
                <p><span className="font-medium">{t('public.intake.new.step1.email')}:</span> {contacts.email}</p>
              </div>
            </div>

            {/* Блок ответов на вопросы */}
            <div className="rounded-lg border border-slate-200 bg-white p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-900">
                  {t('public.intake.new.review.answers')}
                </h2>
                <button
                  type="button"
                  onClick={() => { setCurrentStep('questions'); setCurrentQuestionIndex(0); }}
                  className="text-sm text-brand-600 hover:text-brand-700"
                >
                  {t('public.intake.new.review.edit')}
                </button>
              </div>
              <div className="space-y-2 text-sm">
                {answers.map((answer) => (
                  <p key={answer.questionId}>
                    <span className="font-medium">{t(`public.intake.new.questions.${answer.questionId}.title`)}:</span>{' '}
                    {Array.isArray(answer.value) ? answer.value.join(', ') : String(answer.value)}
                  </p>
                ))}
              </div>
            </div>

            {/* Блок опыта работы */}
            <div className="rounded-lg border border-slate-200 bg-white p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-900">
                  {t('public.intake.new.review.employment')}
                </h2>
                <button
                  type="button"
                  onClick={() => setCurrentStep('employment')}
                  className="text-sm text-brand-600 hover:text-brand-700"
                >
                  {t('public.intake.new.review.edit')}
                </button>
              </div>
              <div className="space-y-3">
                {employments.map((emp, index) => (
                  <div key={index} className="text-sm">
                    <p className="font-medium">{emp.employer_name}</p>
                    <p className="text-slate-600">{emp.position} · {emp.country} · {emp.start_date} → {emp.currently_employed ? t('public.intake.new.employment.current') : emp.end_date}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Блок документов */}
            <div className="rounded-lg border border-slate-200 bg-white p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-900">
                  {t('public.intake.new.review.documents')}
                </h2>
                <button
                  type="button"
                  onClick={() => { setCurrentStep('documents'); setCurrentDocumentIndex(0); }}
                  className="text-sm text-brand-600 hover:text-brand-700"
                >
                  {t('public.intake.new.review.edit')}
                </button>
              </div>
              <div className="space-y-2 text-sm">
                {Object.entries(documents).map(([type, entry]) => (
                  <div key={type} className="flex items-center justify-between">
                    <span>{t(`public.intake.new.documents.${type}.title`)}</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      entry.status === 'uploaded' ? 'bg-green-100 text-green-700' :
                      entry.status === 'in_progress' ? 'bg-amber-100 text-amber-700' :
                      'bg-slate-100 text-slate-700'
                    }`}>
                      {t(`public.intake.new.documents.status.${entry.status}`)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Согласия */}
            <div className="rounded-lg border border-slate-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">
                {t('public.intake.new.review.agreements')}
              </h2>
              <div className="space-y-5">
                <label className="flex items-start gap-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 accent-brand-600"
                    checked={apiFormData?.agreements?.general || false}
                    onChange={(e) => apiUpdateAgreements({ general: e.target.checked })}
                  />
                  <span>
                    {t('public.intake.forms.agreements.general')}{' '}
                    <a href="/legal/rodo.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
                      {t('public.portal.landing.footer.links.rodo', { defaultValue: 'RODO' })}
                    </a>
                    {' · '}
                    <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
                      {t('public.intake.forms.agreements.privacy_link')}
                    </a>
                    .
                  </span>
                </label>
                <label className="flex items-start gap-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 accent-brand-600"
                    checked={apiFormData?.agreements?.employer_share || false}
                    onChange={(e) => apiUpdateAgreements({ employer_share: e.target.checked })}
                  />
                  <span>{t('public.intake.forms.agreements.employer_share')}</span>
                </label>
                <label className="flex items-start gap-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 accent-brand-600"
                    checked={apiFormData?.agreements?.terms_acceptance || false}
                    onChange={(e) => apiUpdateAgreements({ terms_acceptance: e.target.checked })}
                  />
                  <span>
                    {t('public.intake.forms.agreements.terms')}{' '}
                    <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
                      {t('public.intake.forms.agreements.terms_link')}
                    </a>{' '}
                    ·{' '}
                    <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
                      {t('public.intake.forms.agreements.privacy_link')}
                    </a>
                  </span>
                </label>
                <p className="text-xs text-slate-500">{t('public.intake.forms.agreements.cookies_hint')}</p>
                <label className="flex items-start gap-3 text-sm text-slate-700 mt-4">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 accent-brand-600"
                    checked={subscribeNotifications}
                    onChange={(e) => setSubscribeNotifications(e.target.checked)}
                  />
                  <span>{t('public.intake.new.review.subscribe_notifications', { defaultValue: 'Chcę otrzymywać powiadomienia o zmianie statusu zgłoszenia' })}</span>
                </label>
                <LegalLinksBlock className="mt-3" />
              </div>
              
              {(!apiFormData?.agreements?.general || !apiFormData?.agreements?.employer_share || !apiFormData?.agreements?.terms_acceptance) && (
                <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  {t('public.intake.forms.agreements.validation')}
                </p>
              )}
            </div>

            <form onSubmit={async (e) => {
              e.preventDefault()
              if (!token) {
                setError(t('public.intake.new.errors.no_token'))
                return
              }
              
              setError(null)
              
              // ВАЖНО: Проверяем согласия из состояния, а не из DOM
              const generalConsent = Boolean(apiFormData?.agreements?.general)
              const employerConsent = Boolean(apiFormData?.agreements?.employer_share)
              const termsAccepted = Boolean(apiFormData?.agreements?.terms_acceptance)
              
              if (!generalConsent || !employerConsent || !termsAccepted) {
                setError(t('public.intake.new.review.errors.consents_required'))
                return
              }
              
              try {
                // Отправляем анкету
                await apiSubmit({
                  consents: {
                    general: generalConsent,
                    employer_share: employerConsent,
                    terms_acceptance: termsAccepted,
                  },
                  documents_version: CONSENT_DOCUMENT_VERSIONS,
                  cookies_accepted: isCookieConsentGranted(),
                })
                
                if (subscribeNotifications && token && (contacts.email || contacts.phone)) {
                  try {
                    const phoneVal = contacts.phone?.replace(/\s/g, '')
                    await subscribeToNotifications({
                      token,
                      email: contacts.email || undefined,
                      phone: phoneVal ? `${contacts.phone_country_code || '+48'}${phoneVal}` : undefined,
                      subscribe_document_status: true,
                      subscribe_stage_changes: true,
                      subscribe_reminders: true,
                    })
                  } catch {
                    // ignore subscription errors
                  }
                }
                
                setCurrentStep('thank_you')
              } catch (err: any) {
                setError(err?.response?.data?.detail || err?.message || t('public.intake.new.errors.submit_failed'))
              }
            }}>
              {(error || apiError) && (
                <div className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">
                  {error || apiError}
                </div>
              )}
              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-lg bg-brand-600 px-4 py-3 text-white font-semibold shadow-sm transition hover:bg-brand-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
              >
                {submitting ? t('public.intake.new.review.submitting') : t('public.intake.new.review.submit')}
              </button>
            </form>
          </div>
        </div>
      </PublicPageShell>
    )
  }

  // Экран "Спасибо"
  if (currentStep === 'thank_you') {
    const statusToken = apiState?.status_share_token || token
    const statusUrl = statusToken ? `${typeof window !== 'undefined' ? window.location.origin : ''}/public/status/${statusToken}` : ''
    const handleCopyStatusLink = () => {
      if (!statusUrl) return
      navigator.clipboard?.writeText(statusUrl).then(() => {
        notify({ title: t('public.intake.new.thank_you.link_copied', { defaultValue: 'Link skopiowany' }), variant: 'success' })
      }).catch(() => {})
    }
    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="xl" headerExtra={<PublicLocaleSwitcher />}>
        <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card text-center">
          <div className="mb-6">
            <div className="text-6xl mb-4">✅</div>
            <h1 className="text-2xl font-semibold text-slate-900 mb-2">
              {t('public.intake.new.thank_you.title')}
            </h1>
            <p className="text-slate-600">
              {t('public.intake.new.thank_you.message')}
            </p>
          </div>
          {statusUrl && (
            <div className="mb-6 rounded-xl border border-brand-200 bg-brand-50/50 p-4 text-left">
              <p className="text-sm font-medium text-slate-700 mb-2">{t('public.intake.new.thank_you.track_status', { defaultValue: 'Śledź status swojej zgłoszenia' })}</p>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-4">
                <div className="flex flex-col items-center gap-1">
                  <QrCodeCanvas value={statusUrl} size={120} className="rounded-lg" />
                  <p className="text-xs text-slate-500">{t('public.intake.new.thank_you.qr_hint', { defaultValue: 'Zeskanuj, aby dodać link na telefon' })}</p>
                </div>
                <div className="flex flex-col gap-2">
                  <Link
                    to={`/public/status/${statusToken}`}
                    className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
                  >
                    {t('public.intake.new.thank_you.open_status', { defaultValue: 'Otwórz stronę statusu' })}
                  </Link>
                  <button
                    type="button"
                    onClick={handleCopyStatusLink}
                    className="inline-flex items-center justify-center rounded-lg border border-brand-200 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
                  >
                    {t('public.intake.new.thank_you.copy_link', { defaultValue: 'Skopiuj link' })}
                  </button>
                </div>
              </div>
            </div>
          )}
          <div className="mb-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left">
            <p className="text-sm font-medium text-slate-700 mb-2">
              {t('public.intake.new.thank_you.telegram_title', { defaultValue: 'Telegram assistant' })}
            </p>
            <p className="text-sm text-slate-600 mb-3">
              {t('public.intake.new.thank_you.telegram_hint', { defaultValue: 'Open bot and send your email or phone number to link your profile and track status updates.' })}
            </p>
            <a
              href={telegramBotUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              {t('public.intake.new.thank_you.telegram_open', { defaultValue: 'Open Telegram bot' })}
            </a>
          </div>
          <button
            type="button"
            onClick={() => setCurrentStep('overview')}
            className="rounded-lg bg-brand-600 px-6 py-3 text-white font-semibold shadow-sm transition hover:bg-brand-700"
          >
            {t('public.intake.new.thank_you.go_to_overview')}
          </button>
        </div>
      </PublicPageShell>
    )
  }

  // Обзор после отправки
  if (currentStep === 'overview') {
    return (
      <PublicPageShell topBanner={clientIntakeTopBanner} maxWidth="5xl" headerExtra={<PublicLocaleSwitcher />}>
        <div className="rounded-3xl border border-brand-100 bg-white/95 p-8 shadow-card">
          <h1 className="text-2xl font-semibold text-slate-900 mb-6">
            {t('public.intake.new.overview.title')}
          </h1>

          {/* Прогресс-бар трудоустройства */}
          <div className="space-y-4">
            {/* Этап 1: Проверка анкеты и документов */}
            <div className="flex items-center gap-4">
              <div className="h-8 w-8 rounded-full bg-green-500 flex items-center justify-center text-white">
                ✓
              </div>
              <div className="flex-1">
                <p className="font-semibold text-slate-900">
                  {t('public.intake.new.overview.stage1')}
                </p>
                <p className="text-sm text-slate-600">
                  {t('public.intake.new.overview.stage1_status')}
                </p>
              </div>
            </div>

            {/* Остальные этапы - заглушки */}
            {[2, 3, 4, 5, 6].map((stage) => (
              <div key={stage} className="flex items-center gap-4">
                <div className="h-8 w-8 rounded-full bg-slate-300 flex items-center justify-center text-white">
                  {stage}
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-slate-900">
                    {t(`public.intake.new.overview.stage${stage}`)}
                  </p>
                  <p className="text-sm text-slate-600">
                    {t('public.intake.new.overview.pending')}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {(apiState?.status_share_token || token) && (
            <div className="mt-6 rounded-xl border border-brand-200 bg-brand-50/50 p-4">
              <p className="text-sm font-medium text-slate-700 mb-3">{t('public.intake.new.thank_you.track_status', { defaultValue: 'Śledź status swojej zgłoszenia' })}</p>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-4">
                <div className="flex flex-col items-center gap-1">
                  <QrCodeCanvas value={`${typeof window !== 'undefined' ? window.location.origin : ''}/public/status/${apiState?.status_share_token || token}`} size={120} className="rounded-lg" />
                  <p className="text-xs text-slate-500">{t('public.intake.new.thank_you.qr_hint', { defaultValue: 'Zeskanuj, aby dodać link na telefon' })}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link
                    to={`/public/status/${apiState?.status_share_token || token}`}
                    className="inline-flex rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
                  >
                    {t('public.intake.new.thank_you.open_status', { defaultValue: 'Otwórz stronę statusu' })}
                  </Link>
                  <button
                    type="button"
                    onClick={() => {
                      const url = `${typeof window !== 'undefined' ? window.location.origin : ''}/public/status/${apiState?.status_share_token || token}`
                      navigator.clipboard?.writeText(url).then(() => {
                        notify({ title: t('public.intake.new.thank_you.link_copied', { defaultValue: 'Link skopiowany' }), variant: 'success' })
                      }).catch(() => {})
                    }}
                    className="inline-flex rounded-lg border border-brand-200 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
                  >
                    {t('public.intake.new.thank_you.copy_link', { defaultValue: 'Skopiuj link' })}
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="mt-8 rounded-lg border border-brand-200 bg-brand-50/30 p-4 text-center">
            <p className="text-sm text-slate-700 mb-2">
              {t('public.intake.new.overview.contact_hint')}
            </p>
            {contacts.phone && (
              <a
                href={`https://wa.me/${contacts.phone?.replace(/\D/g, '')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block rounded-lg bg-green-600 px-4 py-2 text-white font-semibold hover:bg-green-700 transition"
              >
                {t('public.intake.new.overview.contact_manager')}
              </a>
            )}
          </div>
        </div>
      </PublicPageShell>
    )
  }

  // Заглушка (не должна достигнуться)
  return null
}
