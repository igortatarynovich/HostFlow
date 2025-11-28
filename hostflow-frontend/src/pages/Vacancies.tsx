// src/pages/Vacancies.tsx
import React from 'react'
import VacancyList from '../components/vacancies/VacancyList'

const VacanciesPage: React.FC = () => {
  return (
    <div className="h-full w-full flex flex-col space-y-4">

      <div>
        <VacancyList />
      </div>
    </div>
  )
}

export default VacanciesPage