/**
 * Historical one-shot (2026-05): replaced layout *-[Npx] with `hf-*` tokens / scale.
 * Kept for reference if reviving old branches; baseline is clean (`ui:adr011:check --fail`).
 */
import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const srcDir = path.join(root, 'src')

const IGNORE_DIRS = new Set(['dist', 'node_modules', 'i18n'])
const IGNORE_FILES = [/\.test\./, /\.spec\./, /\.d\.ts$/]

/** Longest match first */
const REPLACEMENTS = [
  ['max-w-[1600px]', 'max-w-hf-1600'],
  ['max-w-[1200px]', 'max-w-hf-1200'],
  ['sm:min-w-[180px]', 'sm:min-w-hf-180'],
  ['sm:min-w-[100px]', 'sm:min-w-hf-100'],
  ['max-h-[520px]', 'max-h-hf-520'],
  ['max-h-[420px]', 'max-h-hf-420'],
  ['max-h-[400px]', 'max-h-hf-400'],
  ['max-h-[280px]', 'max-h-hf-280'],
  ['min-w-[980px]', 'min-w-hf-980'],
  ['min-w-[720px]', 'min-w-hf-720'],
  ['min-w-[640px]', 'min-w-hf-640'],
  ['min-w-[520px]', 'min-w-hf-520'],
  ['min-w-[420px]', 'min-w-hf-420'],
  ['min-w-[280px]', 'min-w-hf-280'],
  ['min-w-[260px]', 'min-w-hf-260'],
  ['min-w-[240px]', 'min-w-hf-240'],
  ['min-w-[220px]', 'min-w-hf-220'],
  ['min-w-[200px]', 'min-w-hf-200'],
  ['min-w-[190px]', 'min-w-hf-190'],
  ['min-w-[180px]', 'min-w-hf-180'],
  ['min-w-[170px]', 'min-w-hf-170'],
  ['min-w-[160px]', 'min-w-hf-160'],
  ['min-w-[140px]', 'min-w-hf-140'],
  ['min-w-[130px]', 'min-w-hf-130'],
  ['min-w-[120px]', 'min-w-hf-120'],
  ['min-w-[100px]', 'min-w-hf-100'],
  ['max-w-[280px]', 'max-w-hf-280'],
  ['max-w-[220px]', 'max-w-hf-220'],
  ['max-w-[200px]', 'max-w-hf-200'],
  ['max-w-[180px]', 'max-w-hf-180'],
  ['max-w-[160px]', 'max-w-hf-160'],
  ['max-w-[140px]', 'max-w-hf-140'],
  ['max-w-[130px]', 'max-w-hf-130'],
  ['max-w-[120px]', 'max-w-hf-120'],
  ['max-w-[104px]', 'max-w-hf-104'],
  ['max-w-[96px]', 'max-w-hf-96'],
  ['max-w-[340px]', 'max-w-hf-340'],
  ['w-[240px]', 'w-hf-240'],
  ['w-[220px]', 'w-hf-220'],
  ['w-[200px]', 'w-hf-200'],
  ['w-[52px]', 'w-hf-52'],
  ['w-[44px]', 'w-11'],
  ['min-w-[22px]', 'min-w-5.5'],
  ['min-w-[20px]', 'min-w-5'],
  ['min-h-[140px]', 'min-h-hf-140'],
  ['min-h-[120px]', 'min-h-30'],
  ['min-h-[100px]', 'min-h-hf-100'],
  ['min-h-[96px]', 'min-h-24'],
  ['min-h-[92px]', 'min-h-23'],
  ['min-h-[90px]', 'min-h-22.5'],
  ['min-h-[80px]', 'min-h-20'],
  ['min-h-[72px]', 'min-h-18'],
  ['min-h-[64px]', 'min-h-16'],
  ['min-h-[52px]', 'min-h-hf-52'],
  ['min-h-[46px]', 'min-h-11.5'],
  ['min-h-[44px]', 'min-h-11'],
  ['min-h-[40px]', 'min-h-10'],
  ['min-h-[36px]', 'min-h-9'],
  ['min-h-[34px]', 'min-h-8.5'],
  ['top-[18px]', 'top-4.5'],
  ['left-[9px]', 'left-2.25'],
  ['mt-[3px]', 'mt-0.5'],
  ['-mb-[1px]', '-mb-px'],
  ['h-[22px]', 'h-5.5'],
  ['w-[22px]', 'w-5.5'],
  ['h-[18px]', 'h-4.5'],
  ['w-[18px]', 'w-4.5'],
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

function migrateFile(file) {
  let text = fs.readFileSync(file, 'utf8')
  const before = text
  for (const [from, to] of REPLACEMENTS) {
    text = text.split(from).join(to)
  }
  if (text !== before) {
    fs.writeFileSync(file, text, 'utf8')
    return true
  }
  return false
}

function main() {
  if (process.env.ALLOW_MIGRATE !== '1') {
    console.error(
      'migrate-adr011-arbitrary-px: baseline already migrated. Set ALLOW_MIGRATE=1 to run (old branches only).',
    )
    process.exit(1)
  }
  const files = walk(srcDir)
  let n = 0
  for (const f of files) {
    if (migrateFile(f)) {
      n += 1
      console.log(path.relative(root, f))
    }
  }
  console.log(`Updated ${n} files`)
}

main()
