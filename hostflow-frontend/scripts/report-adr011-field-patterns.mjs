/**
 * ADR-011 §7: inventory of native form controls that may lack shared field classes (`.input`, `.textarea`).
 *
 * TypeScript AST (same approach as button report).
 *
 *   node scripts/report-adr011-field-patterns.mjs           # exit 0, summary + JSON report
 *   node scripts/report-adr011-field-patterns.mjs --fail   # exit 1 if missing count > scripts/adr011-field-baseline.json
 *
 * Heuristics (reduce noise):
 * - Skip `<input type="hidden" | "checkbox" | "radio" | "file" />` (often styled differently).
 * - Skip if opening tag text matches `\\binput\\b` or `\\btextarea\\b` (Tailwind @layer class names).
 * - Per-line: `adr011-field-ignore` skips that opening.
 */
import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const root = process.cwd()
const srcDir = path.join(root, 'src')
const fail = process.argv.includes('--fail')
const baselineFile = path.join(root, 'scripts', 'adr011-field-baseline.json')

const IGNORE_DIRS = new Set(['dist', 'node_modules', 'i18n'])
const IGNORE_FILES = [/\.test\./, /\.spec\./, /\.d\.ts$/]

function hasFieldToken(tagText) {
  return /\binput\b/.test(tagText) || /\btextarea\b/.test(tagText)
}

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

function scriptKindForFile(filePath) {
  return filePath.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
}

function lineNumberAtPosition(sf, pos) {
  return sf.getLineAndCharacterOfPosition(pos).line + 1
}

function inputTypeFromRaw(raw) {
  const m = /type\s*=\s*["']([^"']+)["']/.exec(raw)
  return m ? m[1].toLowerCase() : ''
}

function shouldSkipInput(raw) {
  const ty = inputTypeFromRaw(raw)
  return ty === 'hidden' || ty === 'checkbox' || ty === 'radio' || ty === 'file'
}

/** @returns {{ eligible: number, hits: Array<{ tag: string, raw: string, line: number }> }} */
function analyzeFields(text, filePath) {
  const kind = scriptKindForFile(filePath)
  const sf = ts.createSourceFile(filePath, text, ts.ScriptTarget.Latest, true, kind)
  const lines = text.split(/\r?\n/)
  let eligible = 0
  const hits = []

  function visit(node) {
    const isOpen = ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)
    if (isOpen && ts.isIdentifier(node.tagName)) {
      const tag = node.tagName.escapedText
      if (tag === 'input' || tag === 'textarea' || tag === 'select') {
        const start = node.getStart(sf)
        const end = node.getEnd()
        const raw = text.slice(start, end)
        if (tag === 'input' && shouldSkipInput(raw)) {
          ts.forEachChild(node, visit)
          return
        }
        eligible += 1
        const line = lineNumberAtPosition(sf, start)
        const lineText = lines[line - 1] ?? ''
        if (!hasFieldToken(raw) && !lineText.includes('adr011-field-ignore')) {
          hits.push({ tag, raw, line })
        }
      }
    }
    ts.forEachChild(node, visit)
  }

  visit(sf)
  return { eligible, hits }
}

function main() {
  const files = walk(srcDir)
  const perFile = []
  let totalEligible = 0
  let missingToken = 0

  for (const file of files) {
    const text = fs.readFileSync(file, 'utf8')
    const lines = text.split(/\r?\n/)
    const { eligible, hits: rawHits } = analyzeFields(text, file)
    totalEligible += eligible
    const hits = rawHits.map(({ tag, raw, line }) => {
      const lineText = lines[line - 1] ?? ''
      const snippet = (raw.includes('\n') ? lineText : raw).trim().slice(0, 220)
      return { tag, line, snippet }
    })
    missingToken += hits.length
    if (hits.length) perFile.push({ file, rel: path.relative(root, file), hits })
  }

  perFile.sort((a, b) => b.hits.length - a.hits.length)

  console.log(
    `ADR-011 §7: field opens without input/textarea class token (heuristic): ${missingToken} of ${totalEligible} eligible`,
  )
  for (const item of perFile.slice(0, 40)) {
    console.log(`${String(item.hits.length).padStart(4, ' ')}  ${item.rel}`)
  }
  if (perFile.length > 40) console.log(`… ${perFile.length - 40} more files`)

  const outPath = path.join(root, 'adr011-field-patterns-report.json')
  fs.writeFileSync(
    outPath,
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        note: 'Intrinsic input/textarea/select (TS AST). Excludes hidden/checkbox/radio/file inputs. Missing word input or textarea in opening tag.',
        total_eligible_field_opens: totalEligible,
        opens_missing_field_token: missingToken,
        files: perFile.map((x) => ({
          file: x.rel,
          count: x.hits.length,
          examples: x.hits.slice(0, 12),
        })),
      },
      null,
      2,
    ) + '\n',
    'utf8',
  )
  console.log(`Report: ${path.relative(root, outPath)}`)

  if (fail) {
    let maxMissing
    try {
      const raw = JSON.parse(fs.readFileSync(baselineFile, 'utf8'))
      maxMissing = Number(raw.maxMissingFieldOpens)
    } catch {
      console.error(`ADR-011 §7: missing or invalid ${path.relative(root, baselineFile)} (required with --fail)`)
      process.exit(1)
    }
    if (!Number.isFinite(maxMissing)) {
      console.error('ADR-011 §7: maxMissingFieldOpens must be a number in adr011-field-baseline.json')
      process.exit(1)
    }
    if (missingToken > maxMissing) {
      console.error(
        `ADR-011 §7 field gate: ${missingToken} opens without input/textarea class token > baseline ${maxMissing}. ` +
          'Add `.input` / `.textarea`, use adr011-field-ignore on the line, or lower baseline only when reducing debt.',
      )
      process.exit(1)
    }
  }
}

main()
