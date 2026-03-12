-- Скрипт для очистки фейковых данных (финальная версия)
-- Оставляет только реальные компании: CITRONEX и POLTRAKT

BEGIN;

DO $$
DECLARE
    citronex_id TEXT := 'ed6e7c5b-bc2f-4194-969d-e78d72d63e69';
    poltrakt_id TEXT := '2b1ca966-e77d-4a45-9fa6-33ef4c7c2cd5';
    
    kierowca_ce_citronex_id TEXT;
    poltrakt_ce_id TEXT;
    pracownik_magazyn_id TEXT;
    
    deleted_count INTEGER;
    fake_candidate_condition TEXT;
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
    
    RAISE NOTICE 'Реальные вакансии: %, %, %', kierowca_ce_citronex_id, poltrakt_ce_id, pracownik_magazyn_id;
    
    -- Удаляем service_orders для фейковых кандидатов (CASCADE удалит связанные записи)
    DELETE FROM service_orders WHERE candidate_id IN (
        SELECT id FROM candidates WHERE deleted_at IS NULL AND (
            first_name IN ('Test', 'Boris', 'Anna', 'Bulk', 'Order', 'Auto', 'Lead', 'Owner', 'Final', 'Existing', 'Manual', 'Candidate', 'Draft', 'Flow', 'Assigned', 'Driver', 'Fallback', 'Stage')
            OR last_name IN ('Declined', 'Awaiting', 'Candidate', 'Flow', 'Assigned', 'Driver', 'Fallback', 'Stage', 'Draft')
            OR LOWER(first_name || ' ' || last_name) LIKE '%test%'
            OR LOWER(first_name || ' ' || last_name) LIKE '%demo%'
            OR LOWER(first_name || ' ' || last_name) LIKE '%draft%'
            OR LOWER(first_name || ' ' || last_name) LIKE '%flow%'
            OR LOWER(first_name || ' ' || last_name) LIKE '%assigned%'
            OR short_id LIKE 'TMP%' OR short_id LIKE 'CND999%' OR short_id LIKE 'CND000%'
            OR (company_id IS NOT NULL AND company_id NOT IN (citronex_id, poltrakt_id))
            OR (vacancy_id IS NOT NULL AND vacancy_id != '' AND vacancy_id NOT IN (COALESCE(kierowca_ce_citronex_id, ''), COALESCE(poltrakt_ce_id, ''), COALESCE(pracownik_magazyn_id, '')))
        )
    );
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Удалено service_orders: %', deleted_count;
    
    -- Удаляем документы
    DELETE FROM documents WHERE candidate_id IN (
        SELECT id FROM candidates WHERE deleted_at IS NULL AND (
            first_name IN ('Test', 'Boris', 'Anna', 'Bulk', 'Order', 'Auto', 'Lead', 'Owner', 'Final', 'Existing', 'Manual', 'Candidate', 'Draft', 'Flow', 'Assigned', 'Driver', 'Fallback', 'Stage')
            OR last_name IN ('Declined', 'Awaiting', 'Candidate', 'Flow', 'Assigned', 'Driver', 'Fallback', 'Stage', 'Draft')
            OR LOWER(first_name || ' ' || last_name) LIKE '%test%'
            OR LOWER(first_name || ' ' || last_name) LIKE '%demo%'
            OR LOWER(first_name || ' ' || last_name) LIKE '%draft%'
            OR LOWER(first_name || ' ' || last_name) LIKE '%flow%'
            OR LOWER(first_name || ' ' || last_name) LIKE '%assigned%'
            OR short_id LIKE 'TMP%' OR short_id LIKE 'CND999%' OR short_id LIKE 'CND000%'
            OR (company_id IS NOT NULL AND company_id NOT IN (citronex_id, poltrakt_id))
            OR (vacancy_id IS NOT NULL AND vacancy_id != '' AND vacancy_id NOT IN (COALESCE(kierowca_ce_citronex_id, ''), COALESCE(poltrakt_ce_id, ''), COALESCE(pracownik_magazyn_id, '')))
        )
    );
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Удалено документов: %', deleted_count;
    
    -- Удаляем фейковых кандидатов
    DELETE FROM candidates
    WHERE deleted_at IS NULL
      AND (
        first_name IN ('Test', 'Boris', 'Anna', 'Bulk', 'Order', 'Auto', 'Lead', 'Owner', 'Final', 'Existing', 'Manual', 'Candidate', 'Draft', 'Flow', 'Assigned', 'Driver', 'Fallback', 'Stage')
        OR last_name IN ('Declined', 'Awaiting', 'Candidate', 'Flow', 'Assigned', 'Driver', 'Fallback', 'Stage', 'Draft')
        OR LOWER(first_name || ' ' || last_name) LIKE '%test%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%demo%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%draft%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%flow%'
        OR LOWER(first_name || ' ' || last_name) LIKE '%assigned%'
        OR short_id LIKE 'TMP%' OR short_id LIKE 'CND999%' OR short_id LIKE 'CND000%'
        OR (company_id IS NOT NULL AND company_id NOT IN (citronex_id, poltrakt_id))
        OR (vacancy_id IS NOT NULL 
            AND vacancy_id != ''
            AND vacancy_id NOT IN (COALESCE(kierowca_ce_citronex_id, ''), COALESCE(poltrakt_ce_id, ''), COALESCE(pracownik_magazyn_id, '')))
      );
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Удалено кандидатов: %', deleted_count;
    
    -- Удаляем фейковые вакансии
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
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Удалено вакансий: %', deleted_count;
    
    -- Удаляем фейковые компании
    DELETE FROM companies
    WHERE id NOT IN (citronex_id, poltrakt_id);
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Удалено компаний: %', deleted_count;
    
END $$;

COMMIT;
