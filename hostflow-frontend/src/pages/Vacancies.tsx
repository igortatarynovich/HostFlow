// src/pages/Vacancies.tsx
import React from 'react'
import VacancyList from '../components/vacancies/VacancyList'

const VacanciesPage: React.FC = () => {
  return (
    <div className="flex h-full min-h-0 w-full flex-1 flex-col space-y-0 gap-0">

      <div>
        <VacancyList />
      </div>
    </div>
  )
}

export default VacanciesPage