/**
 * ADR-011 §9: inventory of direct locale date/time formatting in UI code.
 * Prefer shared helpers (`src/utils/dateFormat.ts`, `Intl.*` wrappers) and workspace locale.
 *
 *   node scripts/report-adr011-date-patterns.mjs           # exit 0, summary + JSON report
 *   node scripts/report-adr011-date-patterns.mjs --fail    # exit 1 if hits > scripts/adr011-date-baseline.json maxNonHelperHits
 *
 * Per-line suppress: include `adr011-date-ignore` on the line.
 */
import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const srcDir = path.join(root, 'src')
const fail = process.argv.includes('--fail')
const baselineFile = path.join(root, 'scripts', 'adr011-date-baseline.json')

const IGNORE_DIRS = new Set(['dist', 'node_modules', 'i18n'])
const IGNORE_FILES = [/\.test\./, /\.spec\./, /\.d\.ts$/]

const PATTERNS = [
  { name: 'toLocaleString(', re: /\.toLocaleString\s*\(/ },
  { name: 'toLocaleDateString(', re: /\.toLocaleDateString\s*\(/ },
  { name: 'toLocaleTimeString(', re: /\.toLocaleTimeString\s*\(/ },
]

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

function isKnownHelper(file) {
  const n = file.replace(/\\/g, '/')
  return (
    n.endsWith('/utils/dateFormat.ts') ||
    n.endsWith('/utils/numberFormat.ts') ||
    n.endsWith('/modules/documents/documentUtils.ts') ||
    n.endsWith('/modules/fleet/fleetCalendarUtc.ts')
  )
}

function scanFile(file) {
  const text = fs.readFileSync(file, 'utf8')
  const lines = text.split(/\r?\n/)
  const hits = []
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]
    if (line.includes('adr011-date-ignore')) continue
    for (const { name, re } of PATTERNS) {
      re.lastIndex = 0
      if (re.test(line)) {
        hits.push({ line: i + 1, kind: name, snippet: line.trim().slice(0, 160) })
      }
    }
  }
  return hits
}

function main() {
  const files = walk(srcDir)
  const all = []
  for (const file of files) {
    const hits = scanFile(file)
    if (!hits.length) continue
    all.push({ file, rel: path.relative(root, file), hits, helper: isKnownHelper(file) })
  }

  const nonHelper = all.filter((x) => !x.helper)
  const totalHits = nonHelper.reduce((n, x) => n + x.hits.length, 0)
  console.log(`ADR-011 §9 date pattern hits (excluding known helper files): ${totalHits} in ${nonHelper.length} files`)
  console.log(`Known helper files with hits: ${all.filter((x) => x.helper).length}`)
  const sorted = [...nonHelper].sort((a, b) => b.hits.length - a.hits.length)
  for (const item of sorted.slice(0, 40)) {
    console.log(`${String(item.hits.length).padStart(4, ' ')}  ${item.rel}`)
  }
  if (sorted.length > 40) console.log(`… ${sorted.length - 40} more files`)

  const outPath = path.join(root, 'adr011-date-patterns-report.json')
  fs.writeFileSync(
    outPath,
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        total_hits_non_helper: totalHits,
        files: sorted.map((x) => ({
          file: x.rel,
          count: x.hits.length,
          examples: x.hits.slice(0, 15),
        })),
      },
      null,
      2,
    ) + '\n',
    'utf8',
  )
  console.log(`Report: ${path.relative(root, outPath)}`)

  if (fail) {
    let maxHits
    try {
      const raw = JSON.parse(fs.readFileSync(baselineFile, 'utf8'))
      maxHits = Number(raw.maxNonHelperHits)
    } catch {
      console.error(`ADR-011 §9: missing or invalid ${path.relative(root, baselineFile)} (required with --fail)`)
      process.exit(1)
    }
    if (!Number.isFinite(maxHits)) {
      console.error('ADR-011 §9: maxNonHelperHits must be a number in adr011-date-baseline.json')
      process.exit(1)
    }
    if (totalHits > maxHits) {
      console.error(
        `ADR-011 §9 date gate: ${totalHits} non-helper hits > baseline ${maxHits}. ` +
          'Remove direct `.toLocale*(` usage or lower the baseline only when reducing debt.',
      )
      process.exit(1)
    }
  }
}

main()
