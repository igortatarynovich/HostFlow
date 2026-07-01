#!/usr/bin/env node
/**
 * Phase 0 #7: bundle-size budget gate.
 *
 * Runs after `vite build` and walks `dist/assets/*.js`. Compares each entry
 * against the patterns declared in `.bundle-budget.json` and fails when
 * either a per-entry or a total budget is exceeded — preventing a single
 * dependency upgrade or new vendor chunk from silently blowing up
 * first-paint size.
 *
 * Reports raw and gzipped sizes so the reader can decide *which* knob to
 * turn (chunk strategy vs. algorithm vs. feature flag).
 *
 * Usage:
 *   npm run build && npm run bundle:check
 *   node scripts/check-bundle-size.mjs --dist some/other/dist --budget custom.json
 */
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, basename } from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const FRONTEND_ROOT = resolve(__dirname, '..')

const DEFAULTS = {
  dist: resolve(FRONTEND_ROOT, 'dist/assets'),
  budgetFile: resolve(FRONTEND_ROOT, '.bundle-budget.json'),
}

function parseArgs(argv) {
  const out = { ...DEFAULTS }
  for (let i = 2; i < argv.length; i += 1) {
    const flag = argv[i]
    const next = argv[i + 1]
    switch (flag) {
      case '--dist':
        out.dist = resolve(next)
        i += 1
        break
      case '--budget':
        out.budgetFile = resolve(next)
        i += 1
        break
      default:
        if (flag.startsWith('--')) {
          console.error(`[bundle-check] unknown flag: ${flag}`)
          process.exit(2)
        }
    }
  }
  return out
}

function readBudget(path) {
  if (!existsSync(path)) {
    console.error(`[bundle-check] budget file not found: ${path}`)
    process.exit(2)
  }
  try {
    return JSON.parse(readFileSync(path, 'utf-8'))
  } catch (err) {
    console.error(`[bundle-check] malformed JSON in ${path}: ${err.message}`)
    process.exit(2)
  }
}

function listAssets(dir) {
  if (!existsSync(dir) || !statSync(dir).isDirectory()) {
    console.error(
      `[bundle-check] dist assets directory not found: ${dir}\n` +
        'Run `npm run build` first.',
    )
    process.exit(2)
  }
  return readdirSync(dir)
    .filter((name) => name.endsWith('.js'))
    .map((name) => ({
      name,
      path: resolve(dir, name),
    }))
    .filter((f) => statSync(f.path).isFile())
}

function measure(files) {
  const out = []
  for (const file of files) {
    const raw = readFileSync(file.path)
    const gz = gzipSync(raw)
    out.push({
      name: file.name,
      raw: raw.length,
      gzipped: gz.length,
    })
  }
  return out
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

function main() {
  const args = parseArgs(process.argv)
  const budget = readBudget(args.budgetFile)
  const assets = measure(listAssets(args.dist))

  const violations = []
  const totalRaw = assets.reduce((s, a) => s + a.raw, 0)
  const totalGz = assets.reduce((s, a) => s + a.gzipped, 0)

  console.log('='.repeat(78))
  console.log('Phase 0 #7 — bundle-size budget')
  console.log('-'.repeat(78))
  console.log('asset                                         raw        gzipped')
  for (const a of assets) {
    console.log(
      `${a.name.padEnd(44)}  ${formatBytes(a.raw).padStart(10)}  ${formatBytes(
        a.gzipped,
      ).padStart(10)}`,
    )
  }
  console.log('-'.repeat(78))
  console.log(
    `TOTAL                                         ${formatBytes(totalRaw).padStart(
      10,
    )}  ${formatBytes(totalGz).padStart(10)}`,
  )

  // Total budget
  if (budget.total) {
    if (typeof budget.total.raw === 'number' && totalRaw > budget.total.raw) {
      violations.push(
        `TOTAL raw ${formatBytes(totalRaw)} > budget ${formatBytes(budget.total.raw)}`,
      )
    }
    if (typeof budget.total.gzipped === 'number' && totalGz > budget.total.gzipped) {
      violations.push(
        `TOTAL gzipped ${formatBytes(totalGz)} > budget ${formatBytes(budget.total.gzipped)}`,
      )
    }
  }

  // Per-entry budgets — regex match on filename (sans hash).
  for (const entry of budget.entryPoints ?? []) {
    const re = new RegExp(entry.pattern)
    const match = assets.find((a) => re.test(a.name))
    if (!match) {
      console.warn(
        `[bundle-check] WARN — pattern ${entry.pattern} did not match any asset ` +
          '(stale budget entry? manual-chunk rename?)',
      )
      continue
    }
    if (typeof entry.raw === 'number' && match.raw > entry.raw) {
      violations.push(
        `${match.name} raw ${formatBytes(match.raw)} > budget ${formatBytes(entry.raw)}` +
          (entry.note ? `  // ${entry.note}` : ''),
      )
    }
    if (typeof entry.gzipped === 'number' && match.gzipped > entry.gzipped) {
      violations.push(
        `${match.name} gzipped ${formatBytes(match.gzipped)} > budget ${formatBytes(
          entry.gzipped,
        )}` + (entry.note ? `  // ${entry.note}` : ''),
      )
    }
  }

  console.log('='.repeat(78))
  if (violations.length > 0) {
    console.error('[bundle-check] FAIL — budget exceeded:')
    for (const v of violations) console.error(`  - ${v}`)
    console.error(
      '\n  → Either shrink the bundle (lazy-load, tree-shake, dedupe) or update ' +
        '`.bundle-budget.json` in a reviewable PR. Every bump is a perf cost.',
    )
    process.exit(1)
  }
  console.log('[bundle-check] OK — all budgets respected.')
}

main()
