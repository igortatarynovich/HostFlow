-- Скрипт для удаления тестовых данных из базы данных
-- Удаляет компании, вакансии и кандидатов с ключевыми словами в названии

BEGIN;

-- Находим и удаляем кандидатов, связанных с тестовыми компаниями/вакансиями
DELETE FROM candidates
WHERE company_id IN (
    SELECT id FROM companies 
    WHERE LOWER(name) LIKE '%test%' 
       OR LOWER(name) LIKE '%тест%' 
       OR LOWER(name) LIKE '%demo%' 
       OR LOWER(name) LIKE '%демо%'
)
OR vacancy_id IN (
    SELECT id FROM vacancies 
    WHERE LOWER(title) LIKE '%test%' 
       OR LOWER(title) LIKE '%тест%' 
       OR LOWER(title) LIKE '%demo%' 
       OR LOWER(title) LIKE '%демо%'
);

-- Удаляем тестовые вакансии
DELETE FROM vacancies 
WHERE LOWER(title) LIKE '%test%' 
   OR LOWER(title) LIKE '%тест%' 
   OR LOWER(title) LIKE '%demo%' 
   OR LOWER(title) LIKE '%демо%';

-- Удаляем тестовые компании
DELETE FROM companies 
WHERE LOWER(name) LIKE '%test%' 
   OR LOWER(name) LIKE '%тест%' 
   OR LOWER(name) LIKE '%demo%' 
   OR LOWER(name) LIKE '%демо%';

COMMIT;
