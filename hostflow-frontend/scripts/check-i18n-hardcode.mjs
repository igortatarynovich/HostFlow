import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const srcDir = path.join(root, 'src')
const baselinePath = path.join(root, 'scripts', 'i18n-hardcode-cyrillic-baseline.txt')
const writeBaseline = process.argv.includes('--write-baseline')

const IGNORE_DIRS = new Set(['i18n', 'dist', 'node_modules', 'content'])
const IGNORE_PATH_PREFIXES = [
  path.join('src', 'platform', 'icons') + path.sep,
  path.join('src', 'content') + path.sep,
  path.join('src', 'i18n') + path.sep,
]
const IGNORE_FILES = [/\.test\./, /\.spec\./, /\.d\.ts$/]

/** Cyrillic letters — Russian hardcode must not land in UI source. */
const CYRILLIC_RE = /[А-Яа-яЁё]/

function walk(dir, out = []) {
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  for (const entry of entries) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (IGNORE_DIRS.has(entry.name)) continue
      walk(full, out)
      continue
    }
    if (!/\.(ts|tsx)$/.test(entry.name)) continue
    if (IGNORE_FILES.some((re) => re.test(entry.name))) continue
    out.push(full)
  }
  return out
}

function isIgnoredRel(rel) {
  const normalized = rel.split(path.sep).join('/')
  return IGNORE_PATH_PREFIXES.some((prefix) => {
    const p = prefix.split(path.sep).join('/')
    return normalized === p.replace(/\/$/, '') || normalized.startsWith(p)
  })
}

const JSX_TEXT_RE = />\s*([^<{][^<{]*[A-Za-zА-Яа-яЁё][^<{]*)\s*</g
const ATTR_RE =
  /\b(placeholder|title|aria-label|label)\s*=\s*("([^"]*[A-Za-zА-Яа-яЁё][^"]*)"|'([^']*[A-Za-zА-Яа-яЁё][^']*)')/g
const DEFAULT_VALUE_CYR_RE = /defaultValue:\s*(['"`])([^'"`]*[А-Яа-яЁё][^'"`]*)\1/g
/** Quoted string literals containing Cyrillic (UI copy / config labels). */
const STRING_LIT_CYR_RE = /(['"`])([^'"`\n]*[А-Яа-яЁё][^'"`\n]*)\1/g

function shouldIgnoreText(text) {
  const trimmed = text.trim()
  if (!trimmed) return true
  if (trimmed.length < 2) return true
  if (/^[\W\d_]+$/.test(trimmed)) return true
  if (/^(https?:\/\/|\/api\/|[A-Za-z0-9_.-]+\.[A-Za-z]{2,})/.test(trimmed)) return true
  return false
}

function stripComments(line) {
  // Best-effort: drop // comments and /* */ on a single line
  let out = line.replace(/\/\*.*?\*\//g, '')
  const idx = out.indexOf('//')
  if (idx >= 0) out = out.slice(0, idx)
  return out
}

function collectFindings(file) {
  const text = fs.readFileSync(file, 'utf8')
  const lines = text.split(/\r?\n/)
  const findings = []

  for (let i = 0; i < lines.length; i += 1) {
    const rawLine = lines[i]
    const line = stripComments(rawLine)
    if (!line.trim()) continue

    // Existing Latin+Cyrillic JSX/attr scan (report all languages as soft findings)
    if (!(line.includes(' t(') || line.includes('{t(') || line.includes('/* i18n-ignore */'))) {
      let m
      JSX_TEXT_RE.lastIndex = 0
      while ((m = JSX_TEXT_RE.exec(line))) {
        const candidate = (m[1] || '').trim()
        if (shouldIgnoreText(candidate)) continue
        findings.push({
          file,
          line: i + 1,
          kind: 'jsx-text',
          text: candidate,
          cyrillic: CYRILLIC_RE.test(candidate),
        })
      }

      ATTR_RE.lastIndex = 0
      while ((m = ATTR_RE.exec(line))) {
        const attrName = m[1]
        const candidate = (m[3] ?? m[4] ?? '').trim()
        if (shouldIgnoreText(candidate)) continue
        findings.push({
          file,
          line: i + 1,
          kind: `attr:${attrName}`,
          text: candidate,
          cyrillic: CYRILLIC_RE.test(candidate),
        })
      }
    }

    // Hard fail candidates: Cyrillic in defaultValue
    let m
    DEFAULT_VALUE_CYR_RE.lastIndex = 0
    while ((m = DEFAULT_VALUE_CYR_RE.exec(line))) {
      findings.push({
        file,
        line: i + 1,
        kind: 'defaultValue-cyrillic',
        text: (m[2] || '').trim(),
        cyrillic: true,
      })
    }

    // Cyrillic string literals (skip import/require paths)
    if (/^\s*import\s/.test(line) || /require\s*\(/.test(line)) continue
    STRING_LIT_CYR_RE.lastIndex = 0
    while ((m = STRING_LIT_CYR_RE.exec(line))) {
      const candidate = (m[2] || '').trim()
      if (shouldIgnoreText(candidate)) continue
      // Skip object keys used as aliases: `новый: 'new'` — key is unquoted identifier, value is Latin
      // Catch quoted Cyrillic values / labels.
      findings.push({
        file,
        line: i + 1,
        kind: 'string-literal-cyrillic',
        text: candidate,
        cyrillic: true,
      })
    }
  }

  return findings
}

function loadBaseline() {
  if (!fs.existsSync(baselinePath)) return new Set()
  return new Set(
    fs
      .readFileSync(baselinePath, 'utf8')
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith('#')),
  )
}

function main() {
  const files = walk(srcDir).filter((f) => !isIgnoredRel(path.relative(root, f)))
  const all = files.flatMap((file) => collectFindings(file))
  const cyrillic = all.filter((f) => f.cyrillic)

  const byFile = new Map()
  for (const item of cyrillic) {
    const rel = path.relative(root, item.file).split(path.sep).join('/')
    const arr = byFile.get(rel) || []
    arr.push(item)
    byFile.set(rel, arr)
  }

  const sortedFiles = [...byFile.keys()].sort()

  if (writeBaseline) {
    const header = [
      '# Files allowed to still contain Cyrillic UI hardcode.',
      '# Regenerate: npm run i18n:hardcode:check -- --write-baseline',
      '# Goal: shrink this list to empty.',
      '',
    ]
    fs.writeFileSync(baselinePath, header.concat(sortedFiles).join('\n') + '\n', 'utf8')
    console.log(`Wrote baseline (${sortedFiles.length} files) → ${path.relative(root, baselinePath)}`)
    process.exit(0)
  }

  const baseline = loadBaseline()
  const regressions = sortedFiles.filter((f) => !baseline.has(f))

  console.log(`Cyrillic hardcode findings: ${cyrillic.length} in ${sortedFiles.length} files`)
  console.log(`Baseline allowlist: ${baseline.size} files`)

  const top = [...byFile.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 25)
  for (const [file, items] of top) {
    const flag = baseline.has(file) ? 'baseline' : 'NEW'
    console.log(`${items.length.toString().padStart(4, ' ')}  [${flag}]  ${file}`)
  }

  const reportFile = path.join(root, 'i18n-hardcode-report.json')
  fs.writeFileSync(
    reportFile,
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        cyrillic_total: cyrillic.length,
        files: sortedFiles.length,
        regressions,
        by_file: sortedFiles.map((file) => ({
          file,
          count: byFile.get(file).length,
          baseline: baseline.has(file),
          examples: byFile
            .get(file)
            .slice(0, 10)
            .map((x) => ({ line: x.line, kind: x.kind, text: x.text })),
        })),
      },
      null,
      2,
    ) + '\n',
    'utf8',
  )
  console.log(`Report saved to ${path.relative(root, reportFile)}`)

  if (!fs.existsSync(baselinePath)) {
    console.error(
      `\nNo baseline at ${path.relative(root, baselinePath)}. Run:\n  npm run i18n:hardcode:check -- --write-baseline\n`,
    )
    process.exit(1)
  }

  if (regressions.length > 0) {
    console.error(`\nCyrillic hardcode regressions (not in baseline):`)
    for (const file of regressions) {
      console.error(`  - ${file} (${byFile.get(file).length})`)
    }
    console.error(`\nFix the strings or, rarely, refresh baseline after intentional debt.`)
    process.exit(1)
  }

  console.log('No Cyrillic hardcode regressions vs baseline.')
}

main()
