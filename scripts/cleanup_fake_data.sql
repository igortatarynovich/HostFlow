-- Скрипт для очистки фейковых данных
-- Оставляет только реальные компании: CITRONEX и POLTRAKT
-- Сохраняет реальные вакансии и кандидатов

BEGIN;

-- ID реальных компаний
DO $$
DECLARE
    citronex_id TEXT := 'ed6e7c5b-bc2f-4194-969d-e78d72d63e69';
    poltrakt_id TEXT := '2b1ca966-e77d-4a45-9fa6-33ef4c7c2cd5';
    
    -- ID реальных вакансий (которые нужно сохранить)
    kierowca_ce_citronex_id TEXT;
    poltrakt_ce_id TEXT;
    pracownik_magazyn_id TEXT;
    
    fake_candidate_ids TEXT[];
BEGIN
    -- Находим реальные вакансии
    SELECT id INTO kierowca_ce_citronex_id 
    FROM vacancies 
    WHERE company_id = citronex_id 
      AND (LOWER(title) LIKE '%kierowca%ce%' OR title = 'Kierowca C+E')
    LIMIT 1;
    
    SELECT id INTO poltrakt_ce_id 
    FROM vacancies 
    WHERE company_id = poltrakt_id 
      AND (LOWER(title) LIKE '%poltrakt%ce%' OR title = 'Poltrakt C+E')
    LIMIT 1;
    
    SELECT id INTO pracownik_magazyn_id 
    FROM vacancies 
    WHERE company_id = citronex_id 
      AND (LOWER(title) LIKE '%pracownik%magazyn%' OR LOWER(title) LIKE '%magazynier%')
    LIMIT 1;
    
    -- Находим ID фейковых кандидатов
    SELECT ARRAY_AGG(id::TEXT) INTO fake_candidate_ids
    FROM candidates
    WHERE deleted_at IS NULL
      AND (
        -- Фейковые имена
        first_name IN ('Test', 'Boris', 'Anna', 'Bulk', 'Order', 'Auto', 'Lead', 'Owner', 'Final', 'Existing', 'Manual', 'Candidate', 'Draft', 'Flow', 'Assigned', 'Driver', 'Fallback', 'Stage')
        OR last_name IN ('Declined', 'Awaiting', 'Candidate', 'Flow', 'Assigned', 'Driver', 'Fallback', 'Stage', 'Draft')
        OR LOWER(first_name || ' ' || last_name) LIKE '%test%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%demo%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%fake%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%seed%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%example%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%draft%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%flow%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%assigned%'
        OR short_id LIKE 'TMP%'
        OR short_id LIKE 'CND999%'
        OR short_id LIKE 'CND000%'
        -- Кандидаты не связанные с реальными компаниями
        OR (company_id IS NOT NULL AND company_id NOT IN (citronex_id, poltrakt_id))
        -- Кандидаты связанные с фейковыми вакансиями (кроме реальных)
        OR (vacancy_id IS NOT NULL 
            AND vacancy_id != ''
            AND vacancy_id NOT IN (
                COALESCE(kierowca_ce_citronex_id, ''), 
                COALESCE(poltrakt_ce_id, ''), 
                COALESCE(pracownik_magazyn_id, '')
            ))
      );
    
    -- Удаляем документы фейковых кандидатов
    IF fake_candidate_ids IS NOT NULL AND array_length(fake_candidate_ids, 1) > 0 THEN
        DELETE FROM documents WHERE candidate_id = ANY(fake_candidate_ids);
    END IF;
    
    -- Удаляем фейковых кандидатов
    IF fake_candidate_ids IS NOT NULL AND array_length(fake_candidate_ids, 1) > 0 THEN
        DELETE FROM candidates WHERE id = ANY(fake_candidate_ids);
    END IF;
    
    -- Удаляем фейковые вакансии (кроме реальных)
    DELETE FROM vacancies
    WHERE company_id NOT IN (citronex_id, poltrakt_id)
       OR company_id IS NULL
       OR (company_id IN (citronex_id, poltrakt_id) 
           AND id NOT IN (
               COALESCE(kierowca_ce_citronex_id, ''), 
               COALESCE(poltrakt_ce_id, ''), 
               COALESCE(pracownik_magazyn_id, '')
           )
           AND (LOWER(title) LIKE '%[auto]%'
                OR LOWER(title) LIKE '%meta%'
                OR LOWER(title) LIKE '%test%'
                OR LOWER(title) LIKE '%demo%')
       );
    
    -- Удаляем фейковые компании (кроме реальных)
    DELETE FROM companies
    WHERE id NOT IN (citronex_id, poltrakt_id);
    
    RAISE NOTICE 'Очистка завершена. Сохранены вакансии: %, %, %', 
        kierowca_ce_citronex_id, poltrakt_ce_id, pracownik_magazyn_id;
END $$;

COMMIT;
