// src/pages/Vacancies.tsx
import React from 'react'
import { PageBreadcrumb } from '../components/nav/PageBreadcrumb'
import VacancyList from '../components/vacancies/VacancyList'

const VacanciesPage: React.FC = () => {
  return (
    <div className="flex h-full min-h-0 w-full flex-1 flex-col space-y-0 gap-0">
      <div className="px-4 pt-2 pb-1">
        <PageBreadcrumb />
      </div>

      <div>
        <VacancyList />
      </div>
    </div>
  )
}

export default VacanciesPage
