/**
 * ADR-011 §3: flag layout/sizing Tailwind utilities that use arbitrary pixel
 * values (e.g. min-h-[80px], w-[320px]) — prefer theme tokens / 8px grid.
 *
 * Typography-only utilities like text-[11px] are intentionally not flagged here.
 *
 * Suppress per line: include "adr011-allow" or "adr011-ignore" in the same line
 * or in the immediately previous line (e.g. // adr011-allow: textarea min height).
 *
 * Usage:
 *   node scripts/check-adr011-ui-patterns.mjs          # exit 0, print summary + JSON report
 *   node scripts/check-adr011-ui-patterns.mjs --fail   # exit 1 if any findings
 */
import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const srcDir = path.join(root, 'src')

const IGNORE_DIRS = new Set(['dist', 'node_modules'])
const IGNORE_FILES = [/\.test\./, /\.spec\./, /\.d\.ts$/]

const fail = process.argv.includes('--fail')

/** Match token: (boundary)(layout-prefix)-[NNpx] */
const LAYOUT_ARBITRARY_PX = new RegExp(
  '(?:^|[\\s"\'`])' +
    '(?:m[trblxy]?|p[trblxy]?|gap(?:-[xy])?|space-[xy]|w|min-w|max-w|h|min-h|max-h|size|rounded(?:-[trbl]{1,2})?|top|right|bottom|left|inset(?:-[trblxy])?)' +
    '-\\[[0-9]+px\\]',
  'g',
)

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

function lineHasSuppression(line) {
  return /adr011-(allow|ignore)/.test(line)
}

function collectFindings(file) {
  const text = fs.readFileSync(file, 'utf8')
  const lines = text.split(/\r?\n/)
  const findings = []

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]
    const prev = i > 0 ? lines[i - 1] : ''
    if (lineHasSuppression(line) || lineHasSuppression(prev)) continue

    LAYOUT_ARBITRARY_PX.lastIndex = 0
    let m
    while ((m = LAYOUT_ARBITRARY_PX.exec(line))) {
      const token = (m[0] || '').replace(/^[\s"'`]+/, '').trim()
      findings.push({ file, line: i + 1, token, snippet: line.trim().slice(0, 200) })
    }
  }

  return findings
}

function main() {
  const files = walk(srcDir)
  const all = files.flatMap((file) => collectFindings(file))
  const byFile = new Map()
  for (const item of all) {
    const arr = byFile.get(item.file) || []
    arr.push(item)
    byFile.set(item.file, arr)
  }

  const sorted = [...byFile.entries()].sort((a, b) => b[1].length - a[1].length)

  console.log(`ADR-011 layout arbitrary px classes: ${all.length}`)
  for (const [file, items] of sorted.slice(0, 200)) {
    const rel = path.relative(root, file)
    console.log(`${items.length.toString().padStart(4, ' ')}  ${rel}`)
  }
  if (sorted.length > 200) {
    console.log(`… ${sorted.length - 200} more files with findings (see report)`)
  }

  const reportFile = path.join(root, 'adr011-ui-patterns-report.json')
  fs.writeFileSync(
    reportFile,
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        total: all.length,
        fail_mode: fail,
        files: sorted.map(([file, items]) => ({
          file: path.relative(root, file),
          count: items.length,
          examples: items.slice(0, 30).map((x) => ({
            line: x.line,
            token: x.token,
            snippet: x.snippet,
          })),
        })),
      },
      null,
      2,
    ) + '\n',
    'utf8',
  )
  console.log(`Report saved to ${path.relative(root, reportFile)}`)

  if (fail && all.length > 0) {
    console.error('check-adr011-ui-patterns: --fail set and findings present; exiting 1')
    process.exit(1)
  }
}

main()
