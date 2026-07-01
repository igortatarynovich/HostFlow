# Threat Model — Document Uploads

## Assets

- Объектное хранилище / локальный storage, метаданные документов, связь document ↔ candidate ↔ tenant.

## Trust boundaries

- Клиентский браузер, интеграции, virus scanner pipeline.

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| DU-1 | Malware | exe, скрипты внутри PDF/Office |
| DU-2 | MIME/extension spoof | `evil.pdf.exe`, fake `Content-Type` |
| DU-3 | Zip bomb | вложенная распаковка |
| DU-4 | DoS | oversized upload, множество параллельных upload |
| DU-5 | Path traversal | имена файлов, архивы |
| DU-6 | XSS через «preview» | SVG/HTML как документ |

## Митигации (baseline)

- Лимит размера; отказ от опасных типов по умолчанию; magic-byte проверка.
- Имена файлов: нормализация, без `..`, без исполняемых расширений.
- Antivirus / async scan до «trusted» статуса; до скана — restricted access.
- Не отдавать сырой SVG/HTML как inline preview без санитизации.

## Тесты

Матрица из `security-ssot.md` §17C; фикстуры с двойным расширением и неверным MIME.

## Связанные спеки

- `docs/specs/architecture/object_storage.md`
- `docs/specs/modules/documents_workflow_contract.md`
