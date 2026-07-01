#!/usr/bin/env python3
"""Documentation governance lint for HostFlow.

Реализует контракт `docs/governance/documentation-rules.md` § 7 «Lint contract».

Проверки:
  forbidden-filename                — запрещённые суффиксы/паттерны имён (draft, final-v2, и т.д.)
  forbidden-path-canon              — каноническое содержимое в `docs/_drafts/**` или в корне репо
  workflow-without-linkage          — workflow в `docs/specs/workflows/` без inbound reference
  archive-without-canon-replacement — файл в `archive/legacy/<DATE>/` без записи в `archive/legacy/<DATE>/README.md`
  broken-md-link                    — относительная ссылка `[..](..)` указывает в несуществующий файл
  superseded-without-status         — ADR с `Supersedes: ADR-NNN`, но в ADR-NNN нет `Status: Superseded by`
  orphan-canon-doc (warning)        — L1/L2 документ без inbound reference; включается `--check-orphans`

Использование:
  python3 scripts/docs/check_doc_governance.py [--strict] [--check-orphans] [--baseline FILE]
                                               [--init-baseline] [--quiet]

Exit codes:
  0 — всё ок (или все нарушения покрыты baseline)
  1 — найдены нарушения уровня error
  2 — внутренняя ошибка скрипта (плохой baseline / IO)

Авторы: governance package, 2026-05-12.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Каталоги, которые мы не сканируем вообще.
EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    ".venv312",
    "node_modules",
    "dist",
    "build",
    "uploads",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".next",
}

# Файлы Markdown, разрешённые в корне репозитория (всё прочее = forbidden-path-canon).
ROOT_MD_ALLOWLIST = {
    "AGENTS.md",
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "LICENSE.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
}

# Запрещённые паттерны имени файла (см. documentation-rules.md §2.1).
FORBIDDEN_FILENAME_PATTERNS = [
    re.compile(r"-draft(\.[a-z0-9]+)?\.md$", re.IGNORECASE),
    re.compile(r"-draft-v\d+\.md$", re.IGNORECASE),
    re.compile(r"-final\.md$", re.IGNORECASE),
    re.compile(r"-final-v\d+\.md$", re.IGNORECASE),
    re.compile(r"-final-\d+\.md$", re.IGNORECASE),
    re.compile(r"-v\d+-final\.md$", re.IGNORECASE),
    re.compile(r"-old\.md$", re.IGNORECASE),
    re.compile(r"-new\.md$", re.IGNORECASE),
    re.compile(r"-copy\.md$", re.IGNORECASE),
    re.compile(r"-backup\.md$", re.IGNORECASE),
    re.compile(r"-tmp\.md$", re.IGNORECASE),
    re.compile(r"-temp\.md$", re.IGNORECASE),
    re.compile(r"-wip\.md$", re.IGNORECASE),
    re.compile(r"^Untitled.*\.md$", re.IGNORECASE),
    re.compile(r"-Untitled.*\.md$", re.IGNORECASE),
]

# Контейнеры, которые НЕ участвуют в валидации (история, archive, drafts).
ARCHIVE_PREFIX = "archive/"
DRAFTS_PREFIX = "docs/_drafts/"

# Workflow folder и его index.
WORKFLOWS_DIR = "docs/specs/workflows"
WORKFLOWS_INDEX = "docs/specs/workflows/index.md"

# Регекс ссылок markdown — ловит [text](target) и [text](<target>).
MD_LINK_RE = re.compile(r"\[(?:[^\]]*?)\]\(\s*<?([^)\s<>][^)\n<>]*?)>?\s*\)")

# ADR Supersedes/Status patterns
ADR_SUPERSEDES_RE = re.compile(
    r"^\s*\*?\*?Supersedes\*?\*?\s*:\s*(ADR-\d+)", re.IGNORECASE | re.MULTILINE
)
ADR_SUPERSEDED_BY_RE = re.compile(
    r"^\s*\*?\*?Status\*?\*?\s*:\s*Superseded\s+by\s+(ADR-\d+)",
    re.IGNORECASE | re.MULTILINE,
)
ADR_FILENAME_RE = re.compile(r"(ADR-\d+)", re.IGNORECASE)


@dataclass
class Issue:
    rule: str
    severity: str  # "error" | "warning"
    path: str
    message: str
    line: int = 0

    def key(self) -> str:
        # Стабильный ключ для baseline (без line — меняется при правке).
        return f"{self.rule}\t{self.path}\t{self.message}"

    def format(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line else self.path
        return f"[{self.severity:7}] {self.rule:34} {loc} — {self.message}"


@dataclass
class LintResult:
    issues: list[Issue] = field(default_factory=list)
    files_scanned: int = 0

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def iter_md_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        # отрезать запрещённые директории
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
        for name in filenames:
            if name.endswith(".md"):
                yield (Path(dirpath) / name).resolve()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_forbidden_filenames(files: list[Path], result: LintResult) -> None:
    for f in files:
        rel_path = rel(f)
        # archive — это историческая зона; имена там часто «склеены» (workflows-foo.md).
        if rel_path.startswith(ARCHIVE_PREFIX) or rel_path.startswith(DRAFTS_PREFIX):
            continue
        name = f.name
        for pat in FORBIDDEN_FILENAME_PATTERNS:
            if pat.search(name):
                result.add(
                    Issue(
                        rule="forbidden-filename",
                        severity="error",
                        path=rel_path,
                        message=(
                            f"имя файла нарушает §2.1 (паттерн '{pat.pattern}'); "
                            f"переименовать в нейтральное имя или архивировать"
                        ),
                    )
                )
                break


def check_forbidden_paths_for_canon(files: list[Path], result: LintResult) -> None:
    for f in files:
        rel_path = rel(f)
        # 1. Markdown в корне репозитория, не из allowlist.
        if "/" not in rel_path and rel_path.endswith(".md"):
            if rel_path not in ROOT_MD_ALLOWLIST:
                result.add(
                    Issue(
                        rule="forbidden-path-canon",
                        severity="error",
                        path=rel_path,
                        message=(
                            "канонический .md в корне репозитория запрещён "
                            f"(allowlist: {sorted(ROOT_MD_ALLOWLIST)}); "
                            "перенести в docs/* в правильную каноническую папку"
                        ),
                    )
                )


def check_workflow_linkage(files: list[Path], result: LintResult) -> None:
    workflow_dir_abs = (REPO_ROOT / WORKFLOWS_DIR).resolve()
    workflow_files = [
        f for f in files if str(f).startswith(str(workflow_dir_abs) + os.sep)
    ]
    if not workflow_files:
        return

    inbound_index: dict[str, set[str]] = {}
    for f in files:
        rel_path = rel(f)
        if rel_path.startswith(ARCHIVE_PREFIX):
            continue
        text = read_text(f)
        if not text:
            continue
        # для каждой workflow-цели смотрим, упомянут ли её basename в этом файле
        for wf in workflow_files:
            wf_rel = rel(wf)
            wf_basename = wf.name
            # ссылка может быть как «slug.md», так и «workflows/slug.md»
            if wf_basename in text or wf_rel in text:
                # сам себя workflow считать не должен
                if rel_path == wf_rel:
                    continue
                inbound_index.setdefault(wf_rel, set()).add(rel_path)

    # дополнительный source — код (Python / TS / JS): простой grep по basename
    # выполняем компактно, без полнотекстового скана всего репо — только по docs links.
    # (скан кода — ответственность интеграционных проверок; для governance MVP достаточно docs+root)

    # index.md мы исключаем из workflow_files (это сам реестр).
    workflow_index_rel = WORKFLOWS_INDEX
    for wf in workflow_files:
        wf_rel = rel(wf)
        if wf_rel == workflow_index_rel:
            continue
        # research / audit / sync-note — допустимы в workflows/, но всё равно должны иметь inbound
        refs = inbound_index.get(wf_rel, set())
        if not refs:
            result.add(
                Issue(
                    rule="workflow-without-linkage",
                    severity="error",
                    path=wf_rel,
                    message=(
                        f"workflow без inbound reference; добавить запись в "
                        f"`{workflow_index_rel}` или ссылку из ADR/module-scope"
                    ),
                )
            )


def check_archive_canon_replacement(files: list[Path], result: LintResult) -> None:
    archive_root = REPO_ROOT / "archive" / "legacy"
    if not archive_root.exists():
        return

    # Для каждого daily-archive каталога находим README.md и сверяем, что упомянуты все файлы.
    for date_dir in sorted(archive_root.iterdir()):
        if not date_dir.is_dir():
            continue
        readme = date_dir / "README.md"
        if not readme.exists():
            for f in date_dir.iterdir():
                if f.is_file() and f.suffix == ".md":
                    result.add(
                        Issue(
                            rule="archive-without-canon-replacement",
                            severity="error",
                            path=rel(date_dir),
                            message=(
                                "директория archive/legacy/<DATE>/ без README.md; "
                                "создать README с canon replacement"
                            ),
                        )
                    )
            continue
        readme_text = read_text(readme)
        for f in date_dir.iterdir():
            if not f.is_file() or f.suffix != ".md":
                continue
            # README.md, FINAL_REPORT.md и REVIEW_REQUIRED.md — служебные.
            if f.name in {"README.md", "FINAL_REPORT.md", "REVIEW_REQUIRED.md"}:
                continue
            if f.name not in readme_text:
                result.add(
                    Issue(
                        rule="archive-without-canon-replacement",
                        severity="error",
                        path=rel(f),
                        message=(
                            f"файл архива не упомянут в `{rel(readme)}`; "
                            "добавить строку с canon replacement"
                        ),
                    )
                )


def is_external_link(target: str) -> bool:
    t = target.strip().lower()
    if t.startswith("#"):
        return True
    return any(
        t.startswith(prefix)
        for prefix in (
            "http://",
            "https://",
            "mailto:",
            "tel:",
            "ftp://",
            "data:",
            "javascript:",
        )
    )


def check_broken_md_links(files: list[Path], result: LintResult) -> None:
    for f in files:
        rel_path = rel(f)
        # archive — историческая зона; внутренние ссылки в архивированных
        # документах могут указывать на места, существовавшие до перемещения.
        # Не сканируем archive на broken-md-link.
        if rel_path.startswith(ARCHIVE_PREFIX):
            continue
        text = read_text(f)
        if not text:
            continue
        # отрезаем code blocks (```), чтобы не ловить ложные ссылки в примерах
        cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        # отрезаем inline code `...`
        cleaned = re.sub(r"`[^`\n]*`", "", cleaned)
        for m in MD_LINK_RE.finditer(cleaned):
            target_raw = m.group(1).strip()
            if not target_raw:
                continue
            target = target_raw.split("#", 1)[0].split("?", 1)[0].strip()
            if not target:
                continue
            if is_external_link(target_raw):
                continue
            # абсолютные пути с / трактуем как from-repo-root
            if target.startswith("/"):
                resolved = (REPO_ROOT / target.lstrip("/")).resolve()
            elif rel_path.startswith(".github/") and not target.startswith("."):
                # GitHub UI резолвит ссылки в .github/**/*.md от repo-root,
                # а не от папки .github/. Эмулируем это поведение.
                resolved = (REPO_ROOT / target).resolve()
            else:
                resolved = (f.parent / target).resolve()
            # если ссылка ведёт за пределы репо — игнорируем
            try:
                resolved.relative_to(REPO_ROOT)
            except ValueError:
                continue
            if not resolved.exists():
                # вычислить line
                line_no = text.count("\n", 0, m.start()) + 1
                result.add(
                    Issue(
                        rule="broken-md-link",
                        severity="error",
                        path=rel_path,
                        message=f"ссылка `{target_raw}` не существует на диске",
                        line=line_no,
                    )
                )


def check_superseded_adr(files: list[Path], result: LintResult) -> None:
    adr_files: dict[str, Path] = {}
    for f in files:
        m = ADR_FILENAME_RE.match(f.name)
        if not m:
            continue
        if "/architecture/" not in str(f) and "/hr/" not in str(f):
            continue
        adr_id = m.group(1).upper()
        adr_files[adr_id] = f

    for adr_id, f in adr_files.items():
        text = read_text(f)
        for m in ADR_SUPERSEDES_RE.finditer(text):
            target_id = m.group(1).upper()
            target_file = adr_files.get(target_id)
            if not target_file:
                line_no = text.count("\n", 0, m.start()) + 1
                result.add(
                    Issue(
                        rule="superseded-without-status",
                        severity="error",
                        path=rel(f),
                        message=(
                            f"{adr_id} помечен как Supersedes {target_id}, но "
                            f"файл {target_id} не найден в каноне"
                        ),
                        line=line_no,
                    )
                )
                continue
            target_text = read_text(target_file)
            if not ADR_SUPERSEDED_BY_RE.search(target_text):
                line_no = text.count("\n", 0, m.start()) + 1
                result.add(
                    Issue(
                        rule="superseded-without-status",
                        severity="error",
                        path=rel(target_file),
                        message=(
                            f"{adr_id} помечен Supersedes {target_id}, но в "
                            f"{target_id} нет строки `Status: Superseded by {adr_id}`"
                        ),
                        line=1,
                    )
                )


def check_orphan_canon(files: list[Path], result: LintResult) -> None:
    """L1/L2 документы должны иметь хотя бы одну inbound reference.

    Простая эвристика: каноническими считаются документы в:
      - docs/specs/architecture/*.md (кроме самих ADR — у них inbound через module-catalog)
      - docs/<module>/module-scope.md
      - docs/security/*.md (кроме threat-models/* и README.md)
    """
    canon_paths: list[Path] = []
    for f in files:
        rel_path = rel(f)
        if rel_path.startswith(ARCHIVE_PREFIX):
            continue
        if rel_path.startswith("docs/specs/architecture/") and rel_path.endswith(".md"):
            canon_paths.append(f)
        elif rel_path.endswith("/module-scope.md"):
            canon_paths.append(f)
        elif rel_path.startswith("docs/security/") and rel_path.endswith(".md"):
            if "threat-models/" in rel_path:
                continue
            if rel_path.endswith("/README.md"):
                continue
            canon_paths.append(f)

    if not canon_paths:
        return

    # Build a single big text blob from all .md and AGENTS.md
    all_texts: dict[str, str] = {}
    for f in files:
        rel_path = rel(f)
        if rel_path.startswith(ARCHIVE_PREFIX):
            continue
        all_texts[rel_path] = read_text(f)

    for canon_file in canon_paths:
        canon_rel = rel(canon_file)
        canon_basename = canon_file.name
        found = False
        for ref_path, text in all_texts.items():
            if ref_path == canon_rel:
                continue
            if canon_basename in text or canon_rel in text:
                found = True
                break
        if not found:
            result.add(
                Issue(
                    rule="orphan-canon-doc",
                    severity="warning",
                    path=canon_rel,
                    message=(
                        "L1/L2 документ без inbound reference; либо добавить "
                        "ссылку из канона, либо архивировать"
                    ),
                )
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        keys.add(line)
    return keys


def write_baseline(path: Path, issues: list[Issue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({i.key() for i in issues})
    header = (
        "# Documentation governance lint baseline\n"
        "# Auto-generated by scripts/docs/check_doc_governance.py --init-baseline\n"
        "# Format: <rule>\\t<path>\\t<message>\n"
        "# Снимать строки только при фиксе соответствующего нарушения.\n"
    )
    path.write_text(header + "\n".join(keys) + ("\n" if keys else ""), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HostFlow documentation governance lint",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="игнорировать baseline и фейлить на любых ошибках",
    )
    parser.add_argument(
        "--check-orphans",
        action="store_true",
        help="включить проверку orphan-canon-doc (warning по умолчанию)",
    )
    parser.add_argument(
        "--baseline",
        default="scripts/docs/governance_baseline.txt",
        help="путь к baseline (известные нарушения, не блокирующие CI)",
    )
    parser.add_argument(
        "--init-baseline",
        action="store_true",
        help="перезаписать baseline текущими нарушениями",
    )
    parser.add_argument("--quiet", action="store_true", help="меньше вывода")
    args = parser.parse_args(argv)

    baseline_path = (REPO_ROOT / args.baseline).resolve()

    files = list(iter_md_files(REPO_ROOT))
    result = LintResult(files_scanned=len(files))

    check_forbidden_filenames(files, result)
    check_forbidden_paths_for_canon(files, result)
    check_workflow_linkage(files, result)
    check_archive_canon_replacement(files, result)
    check_broken_md_links(files, result)
    check_superseded_adr(files, result)
    if args.check_orphans:
        check_orphan_canon(files, result)

    if args.init_baseline:
        # baseline хранит только error-уровень (warnings и так не блокируют)
        errors = [i for i in result.issues if i.severity == "error"]
        write_baseline(baseline_path, errors)
        if not args.quiet:
            print(
                f"baseline обновлён: {len(errors)} нарушений → {rel(baseline_path)}",
                file=sys.stderr,
            )
        return 0

    baseline = set() if args.strict else load_baseline(baseline_path)

    blocking: list[Issue] = []
    informational: list[Issue] = []
    for issue in result.issues:
        if issue.severity == "warning":
            informational.append(issue)
            continue
        if issue.key() in baseline:
            informational.append(issue)
            continue
        blocking.append(issue)

    if not args.quiet:
        print(f"docs-governance: scanned {result.files_scanned} markdown files")
        if informational:
            print(f"  baseline / warnings: {len(informational)}")
            for issue in informational:
                print(f"    {issue.format()}")
        if blocking:
            print(f"  blocking errors:    {len(blocking)}")
            for issue in blocking:
                print(f"    {issue.format()}")
        if not informational and not blocking:
            print("  ✓ no issues")

    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
