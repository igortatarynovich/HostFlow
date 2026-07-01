// src/pages/Vacancies.tsx
import React from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import VacancyList from '../components/vacancies/VacancyList'

const VacanciesPage: React.FC = () => {
  const { t } = useI18n()
  return (
    <div className="flex h-full min-h-0 w-full flex-1 flex-col space-y-0 gap-0">
      <div className="px-4 pt-2 pb-1">
        <PageHeader
          primaryAction={
            <Link to={CRM_APP_PATHS.vacancyNew} className="btn-primary btn-sm">
              {t('app.vacancies.list.new_vacancy')}
            </Link>
          }
        />
      </div>

      <div>
        <VacancyList />
      </div>
    </div>
  )
}

export default VacanciesPage
