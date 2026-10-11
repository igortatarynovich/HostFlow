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

Authenticated Hub **metadata** resolve is [`documents-platform.md`](./documents-platform.md), not this upload/ACL surface.

## Operator Candidate Card (presentation only)

The operator Candidate Card may show one Documents Hub instance inside Documents and again inside Legalization. That is a second view of the same file, not a second store, a second upload endpoint, or a new public-link type. Upload, candidate upload links, and document ACL stay on the existing Hub. No new candidate field is introduced for work-authorization order dates or procedure states.

## Связанные спеки

- `docs/specs/architecture/object_storage.md`
- `docs/specs/modules/documents_workflow_contract.md`
