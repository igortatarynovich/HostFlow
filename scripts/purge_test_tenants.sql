-- Чистка тестового мусора из прод-БД HostFlow.
-- Подготовлено 2026-07-28. ПЕРЕД ЗАПУСКОМ убедитесь, что есть свежий бэкап:
--   backups/full-pre-tenant-purge-20260728T114548Z.dump  (259 МБ, 264 таблицы)
--
-- Запуск:
--   docker exec -i hostflow-db-1 psql -U hostflow -d hostflow -v ON_ERROR_STOP=1 \
--     < scripts/purge_test_tenants.sql
--
-- Что делает:
--   Фаза A — удаляет все тенанты, кроме трёх рабочих, и все их строки в 228 таблицах.
--   Фаза B — вычищает бизнес-данные внутри служебного тенанта Superadmin
--            (он должен давать сквозной доступ, а не владеть своими кандидатами/лидами/вакансиями)
--            и лишних пользователей в нём.
--   Фаза C — подчищает «сирот» в таблицах без tenant_id и проверяет целостность.
--
-- Всё выполняется одной транзакцией: при любой ошибке — полный откат.
-- session_replication_role = replica временно снимает проверку внешних ключей,
-- чтобы не выстраивать порядок удаления по 228 таблицам; целостность проверяется в фазе C.

BEGIN;
SET LOCAL session_replication_role = replica;

-- ---------------------------------------------------------------- рабочие тенанты
CREATE TEMP TABLE keep_t(id text) ON COMMIT DROP;
INSERT INTO keep_t VALUES
 ('9497fc29-6051-424d-9344-abb4aed9b110'),  -- Focus Personnel — боевой
 ('9e5133ae-b7a3-4b82-b486-e6657be0a3cb'),  -- Игорь — боевой
 ('11111111-1111-1111-1111-111111111111');  -- Superadmin — служебный, данные чистим в фазе B

-- аккаунты, которые остаются в Superadmin
CREATE TEMP TABLE keep_su_users(email text) ON COMMIT DROP;
INSERT INTO keep_su_users VALUES ('admin@hostflow.dev'), ('biuro@work-host.com');

-- ============================================================== ФАЗА A
DO $$
DECLARE r record; n bigint; total bigint := 0;
BEGIN
  FOR r IN SELECT table_name FROM information_schema.columns
           WHERE table_schema='public' AND column_name='tenant_id'
             AND table_name <> 'tenants' ORDER BY table_name
  LOOP
    EXECUTE format(
      'DELETE FROM public.%I WHERE tenant_id::text NOT IN (SELECT id FROM keep_t)', r.table_name);
    GET DIAGNOSTICS n = ROW_COUNT;
    total := total + n;
  END LOOP;
  RAISE NOTICE 'Фаза A: удалено строк в тенантных таблицах: %', total;
END $$;

-- связки агентство↔клиент: убираем всё, что ведёт за пределы рабочих тенантов
-- (client_tenant_id nullable — NULL означает клиента без своего тенанта, такие оставляем)
DELETE FROM tenant_links
WHERE agency_tenant_id::text NOT IN (SELECT id FROM keep_t)
   OR (client_tenant_id IS NOT NULL AND client_tenant_id::text NOT IN (SELECT id FROM keep_t));

DELETE FROM tenants WHERE id::text NOT IN (SELECT id FROM keep_t);

-- ============================================================== ФАЗА B
-- Superadmin не владеет операционными данными. Чистим их, оставляя тенант,
-- его настройки/лицензии/модули и два рабочих аккаунта.
DO $$
DECLARE r record; n bigint; total bigint := 0;
  su text := '11111111-1111-1111-1111-111111111111';
  -- таблицы, которые в Superadmin ДОЛЖНЫ остаться (конфигурация, а не операционка)
  keep_tables text[] := ARRAY[
    'users','user_memberships','user_company_access','tenants','tenant_licenses',
    'tenant_module_installations','module_registry','module_capabilities','module_dependencies',
    'tenant_settings','tenant_email_config','tenant_branding'
  ];
BEGIN
  FOR r IN SELECT table_name FROM information_schema.columns
           WHERE table_schema='public' AND column_name='tenant_id'
             AND table_name <> 'tenants'
             AND NOT (table_name = ANY(keep_tables)) ORDER BY table_name
  LOOP
    EXECUTE format('DELETE FROM public.%I WHERE tenant_id::text = %L', r.table_name, su);
    GET DIAGNOSTICS n = ROW_COUNT;
    total := total + n;
  END LOOP;
  RAISE NOTICE 'Фаза B: удалено операционных строк в Superadmin: %', total;
END $$;

-- лишние аккаунты внутри Superadmin
DELETE FROM user_memberships
WHERE user_id IN (SELECT id FROM users
                  WHERE tenant_id::text='11111111-1111-1111-1111-111111111111'
                    AND email NOT IN (SELECT email FROM keep_su_users));

DELETE FROM users
WHERE tenant_id::text='11111111-1111-1111-1111-111111111111'
  AND email NOT IN (SELECT email FROM keep_su_users);

-- ============================================================== ФАЗА C
-- Снимаем «сирот»: строки, чей внешний ключ указывает в никуда.
-- Повторяем объявленное поведение каждого внешнего ключа, а НЕ удаляем всё подряд:
--   колонка nullable          -> обнуляем ссылку (как ON DELETE SET NULL)
--   колонка NOT NULL          -> строка без родителя нежизнеспособна, удаляем
-- Иначе сносятся живые записи: заметки, журнал, история назначений и даже пользователи,
-- у которых всего лишь удалён руководитель (users.supervisor_id).
--
-- Один проход недостаточен: удаление в таблице X может осиротить строки в таблице Y,
-- которую цикл уже прошёл. Повторяем, пока проходы не перестанут что-либо менять.
DO $$
DECLARE r record; n bigint; pass_total bigint;
        nulled bigint := 0; deleted bigint := 0; pass int := 0;
BEGIN
  LOOP
    pass := pass + 1;
    pass_total := 0;
    FOR r IN
      SELECT src.relname AS src_table, srccol.attname AS src_col,
             tgt.relname AS tgt_table, tgtcol.attname AS tgt_col,
             srccol.attnotnull AS src_notnull
      FROM pg_constraint con
      JOIN pg_class src ON src.oid = con.conrelid
      JOIN pg_class tgt ON tgt.oid = con.confrelid
      JOIN pg_namespace ns ON ns.oid = src.relnamespace AND ns.nspname='public'
      JOIN pg_attribute srccol ON srccol.attrelid=con.conrelid AND srccol.attnum = con.conkey[1]
      JOIN pg_attribute tgtcol ON tgtcol.attrelid=con.confrelid AND tgtcol.attnum = con.confkey[1]
      WHERE con.contype='f' AND array_length(con.conkey,1)=1
    LOOP
      IF r.src_notnull THEN
        EXECUTE format(
          'DELETE FROM public.%I s WHERE s.%I IS NOT NULL
             AND NOT EXISTS (SELECT 1 FROM public.%I t WHERE t.%I = s.%I)',
          r.src_table, r.src_col, r.tgt_table, r.tgt_col, r.src_col);
        GET DIAGNOSTICS n = ROW_COUNT;
        IF n > 0 THEN
          RAISE NOTICE '  проход % — УДАЛЕНО %.% (NOT NULL) -> %.% : %',
                       pass, r.src_table, r.src_col, r.tgt_table, r.tgt_col, n;
          deleted := deleted + n;
        END IF;
      ELSE
        BEGIN
          EXECUTE format(
            'UPDATE public.%I s SET %I = NULL WHERE s.%I IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM public.%I t WHERE t.%I = s.%I)',
            r.src_table, r.src_col, r.src_col, r.tgt_table, r.tgt_col, r.src_col);
          GET DIAGNOSTICS n = ROW_COUNT;
          IF n > 0 THEN
            RAISE NOTICE '  проход % — обнулено %.% -> %.% : %',
                         pass, r.src_table, r.src_col, r.tgt_table, r.tgt_col, n;
            nulled := nulled + n;
          END IF;
        EXCEPTION WHEN check_violation THEN
          -- Колонка формально nullable, но CHECK требует её заполненности
          -- (например ck_tenant_links_client_exactly_one). Без родителя строка
          -- бессмысленна — удаляем её целиком.
          EXECUTE format(
            'DELETE FROM public.%I s WHERE s.%I IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM public.%I t WHERE t.%I = s.%I)',
            r.src_table, r.src_col, r.tgt_table, r.tgt_col, r.src_col);
          GET DIAGNOSTICS n = ROW_COUNT;
          RAISE NOTICE '  проход % — УДАЛЕНО %.% (CHECK не даёт NULL) -> %.% : %',
                       pass, r.src_table, r.src_col, r.tgt_table, r.tgt_col, n;
          deleted := deleted + n;
        END;
      END IF;
      pass_total := pass_total + n;
    END LOOP;
    EXIT WHEN pass_total = 0 OR pass >= 10;
  END LOOP;
  RAISE NOTICE 'Фаза C: обнулено ссылок %, удалено строк % (проходов: %)', nulled, deleted, pass;
END $$;

-- ============================================================== контроль
SELECT 'тенантов осталось'        AS metric, count(*)::text AS value FROM tenants
UNION ALL SELECT 'пользователей',            count(*)::text FROM users
UNION ALL SELECT 'кандидатов Focus Personnel', count(*)::text FROM candidates WHERE tenant_id='9497fc29-6051-424d-9344-abb4aed9b110'
UNION ALL SELECT 'кандидатов Superadmin',    count(*)::text FROM candidates WHERE tenant_id='11111111-1111-1111-1111-111111111111'
UNION ALL SELECT 'кандидатов gma11 (живые)', count(*)::text FROM candidates c JOIN users u ON u.id=c.recruiter_id WHERE u.email LIKE '%@gma11.com'
UNION ALL SELECT 'уведомлений',              count(*)::text FROM notifications;

-- Проверьте цифры выше. Focus Personnel должен остаться 1743, gma11 — 84.
-- Если всё верно:   COMMIT;
-- Если что-то не так: ROLLBACK;
COMMIT;
