#!/usr/bin/env python3
"""
RLS Audit Script
Проверяет все модели на наличие tenant_id и RLS policies в миграциях.
"""
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent))

# Список таблиц, которые НЕ должны иметь tenant_id (системные)
SYSTEM_TABLES = {
    "tenants",  # Сама таблица тенантов
    "alembic_version",  # Версии миграций
    "users",  # Может быть исключением, но обычно имеет tenant_id
}

# Таблицы, которые должны иметь tenant_id, но могут быть исключениями
OPTIONAL_TENANT_TABLES = {
    "audit_log",  # Может хранить глобальный аудит
    "activity_log",  # Может хранить глобальную активность
}


def find_models_with_tenant_id() -> Dict[str, bool]:
    """Находит все модели и проверяет наличие tenant_id."""
    models_dir = Path(__file__).parent.parent / "app" / "models"
    results: Dict[str, bool] = {}
    
    for model_file in models_dir.glob("*.py"):
        if model_file.name.startswith("_") or model_file.name == "base.py":
            continue
            
        content = model_file.read_text(encoding="utf-8")
        
        # Ищем классы, наследующиеся от Base
        class_matches = re.findall(r"class\s+(\w+)\s*\([^)]*Base", content)
        
        for class_name in class_matches:
            # Ищем __tablename__
            table_match = re.search(
                rf'class\s+{class_name}.*?__tablename__\s*=\s*["\'](\w+)["\']',
                content,
                re.DOTALL
            )
            
            if not table_match:
                # Пробуем найти через __table_args__ или другие способы
                # Для простоты используем snake_case от class_name
                table_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
            else:
                table_name = table_match.group(1)
            
            # Проверяем наличие tenant_id
            has_tenant_id = bool(re.search(r'tenant_id\s*[:=]', content))
            results[table_name] = has_tenant_id
    
    return results


def find_rls_policies_in_migrations() -> Dict[str, bool]:
    """Проверяет наличие RLS policies в миграциях Alembic."""
    migrations_dir = Path(__file__).parent.parent / "alembic" / "versions"
    results: Dict[str, bool] = {}
    
    for migration_file in migrations_dir.glob("*.py"):
        if migration_file.name.startswith("__"):
            continue
            
        content = migration_file.read_text(encoding="utf-8")
        
        # Ищем упоминания RLS
        rls_patterns = [
            r"ENABLE ROW LEVEL SECURITY",
            r"CREATE POLICY.*rls_",
            r"ALTER TABLE.*ENABLE ROW LEVEL SECURITY",
        ]
        
        has_rls = any(re.search(pattern, content, re.IGNORECASE) for pattern in rls_patterns)
        
        if has_rls:
            # Извлекаем имена таблиц из миграции
            table_matches = re.findall(
                r"(?:ALTER TABLE|CREATE POLICY|ON)\s+(\w+)",
                content,
                re.IGNORECASE
            )
            
            for table in table_matches:
                if table not in results:
                    results[table] = True
    
    return results


def generate_report() -> None:
    """Генерирует отчет о состоянии RLS."""
    print("=" * 80)
    print("RLS AUDIT REPORT")
    print("=" * 80)
    print()
    
    models = find_models_with_tenant_id()
    rls_policies = find_rls_policies_in_migrations()
    
    print(f"Найдено моделей с tenant_id: {sum(1 for v in models.values() if v)}")
    print(f"Найдено таблиц с RLS policies: {len(rls_policies)}")
    print()
    
    # Таблицы без tenant_id (кроме системных)
    missing_tenant_id: List[str] = []
    for table, has_tenant in models.items():
        if not has_tenant and table not in SYSTEM_TABLES:
            missing_tenant_id.append(table)
    
    if missing_tenant_id:
        print("⚠️  ТАБЛИЦЫ БЕЗ tenant_id:")
        for table in sorted(missing_tenant_id):
            print(f"   - {table}")
        print()
    
    # Таблицы с tenant_id, но без RLS policies
    missing_rls: List[str] = []
    for table, has_tenant in models.items():
        if has_tenant and table not in rls_policies and table not in SYSTEM_TABLES:
            missing_rls.append(table)
    
    if missing_rls:
        print("🔴 КРИТИЧНО: Таблицы с tenant_id, но БЕЗ RLS policies:")
        for table in sorted(missing_rls):
            print(f"   - {table}")
        print()
    
    # Таблицы с RLS, но без tenant_id (ошибка)
    rls_without_tenant: List[str] = []
    for table in rls_policies:
        if table not in models or not models[table]:
            if table not in SYSTEM_TABLES:
                rls_without_tenant.append(table)
    
    if rls_without_tenant:
        print("⚠️  RLS policies для таблиц без tenant_id:")
        for table in sorted(rls_without_tenant):
            print(f"   - {table}")
        print()
    
    # Статистика
    print("=" * 80)
    print("СТАТИСТИКА:")
    print(f"  Всего моделей: {len(models)}")
    print(f"  С tenant_id: {sum(1 for v in models.values() if v)}")
    print(f"  С RLS policies: {len(rls_policies)}")
    print(f"  Требуют RLS: {len(missing_rls)}")
    print("=" * 80)
    
    # Генерируем SQL для создания RLS policies
    if missing_rls:
        print()
        print("SQL для создания RLS policies (PostgreSQL):")
        print("-" * 80)
        for table in sorted(missing_rls):
            print(f"""
-- RLS для {table}
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS rls_{table}_tenant
ON {table}
USING (tenant_id = current_setting('app.tenant_id')::uuid);
""")
        print("-" * 80)


if __name__ == "__main__":
    generate_report()

