import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listCompanies } from '../api/client'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import VacancyDetail from './VacancyDetail'

export default function VacancyDetailRoute() {
  const navigate = useNavigate()
  const [companiesMap, setCompaniesMap] = useState<Record<string, string>>({})

  useEffect(() => {
    let cancelled = false
    listCompanies({ limit: 1000, offset: 0 })
      .then((data: any) => {
        const items: any[] = Array.isArray(data?.items) ? data.items : (Array.isArray(data) ? data : [])
        const map: Record<string, string> = {}
        for (const it of items) {
          const id = it?.id || it?.uuid || it?.company_id
          const name = it?.name || it?.title || it?.label || id
          if (id) map[id] = name
        }
        if (!cancelled) setCompaniesMap(map)
      })
      .catch((err) => {
        console.warn('[VacancyDetailRoute] companies load failed', err)
      })
    return () => { cancelled = true }
  }, [])

  return (
    <VacancyDetail
      item={undefined as any}
      onBack={() => navigate(CRM_APP_PATHS.vacancies)}
      companiesMap={companiesMap}
    />
  )
}
