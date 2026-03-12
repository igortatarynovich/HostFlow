#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..')

const SCENARIO_META = {
  a: {
    label: 'A',
    businessType: 'services',
    steps: [
      'User registered successfully.',
      'Payment completed (or marked BLOCKED if Stripe/webhooks not available).',
      'Business type services selected.',
      'Work email connected.',
      'First client created.',
      'First message sent.',
      'First task created.',
      'Auto-reply configured.',
      'Workflow started end-to-end.',
    ],
  },
  b: {
    label: 'B',
    businessType: 'agency',
    steps: [
      'User registered successfully.',
      'Payment step completed (or marked BLOCKED if Stripe not available).',
      'Business type agency selected.',
      'Ad source connected.',
      'Lead received.',
      'Client created.',
      'Candidate created.',
      'Manager assigned.',
      'Team + roles configured.',
      'Workflow started end-to-end.',
    ],
  },
  c: {
    label: 'C',
    businessType: 'employer',
    steps: [
      'User registered successfully.',
      'Payment step completed (or marked BLOCKED if Stripe not available).',
      'Business type employer selected.',
      'Vacancy created.',
      'Candidate created.',
      'Responsible person assigned.',
      'Statuses configured.',
      'Work email connected.',
      'Hiring workflow started end-to-end.',
    ],
  },
}

function usage(code = 0) {
  const text = [
    'Usage:',
    '  node scripts/create-f7-run-record.mjs --scenario <a|b|c> --env <staging|production> --tenant <slug> --owner "<name/role>" [--date YYYY-MM-DD] [--result PASS|FAIL|BLOCKED|IN_PROGRESS] [--dry-run] [--print-ssot-row]',
    '',
    'Example:',
    '  node scripts/create-f7-run-record.mjs --scenario b --env staging --tenant demo-agency --owner "Product/QA" --dry-run',
  ].join('\n')
  console.log(text)
  process.exit(code)
}

function parseArgs(argv) {
  const out = {
    scenario: '',
    env: '',
    tenant: '',
    owner: '',
    date: '',
    result: 'IN_PROGRESS',
    dryRun: false,
    printSsotRow: false,
  }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--scenario') out.scenario = String(argv[++i] || '').trim().toLowerCase()
    else if (arg === '--env') out.env = String(argv[++i] || '').trim().toLowerCase()
    else if (arg === '--tenant') out.tenant = String(argv[++i] || '').trim()
    else if (arg === '--owner') out.owner = String(argv[++i] || '').trim()
    else if (arg === '--date') out.date = String(argv[++i] || '').trim()
    else if (arg === '--result') out.result = String(argv[++i] || '').trim().toUpperCase()
    else if (arg === '--dry-run') out.dryRun = true
    else if (arg === '--print-ssot-row') out.printSsotRow = true
    else if (arg === '--help' || arg === '-h') usage(0)
    else usage(1)
  }
  return out
}

function todayUtc() {
  return new Date().toISOString().slice(0, 10)
}

function safeSlug(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function buildContent({ scenario, env, tenant, owner, date, result }) {
  const meta = SCENARIO_META[scenario]
  const lines = []
  lines.push(`# F7 Scenario ${meta.label} Run Record`)
  lines.push('')
  lines.push(`Date: \`${date}\`  `)
  lines.push(`Scenario: \`${meta.label}\`  `)
  lines.push(`Business type: \`${meta.businessType}\`  `)
  lines.push(`Environment: \`${env}\`  `)
  lines.push(`Tenant: \`${tenant}\`  `)
  lines.push(`Owner: \`${owner}\`  `)
  lines.push(`Result: \`${result}\`  `)
  lines.push('Blocker (if any): `N/A`')
  lines.push('')
  lines.push('## Step-by-Step Evidence')
  lines.push('')
  lines.push('| Step | Expected | Actual | Status (`PASS/FAIL/BLOCKED`) | Evidence |')
  lines.push('|---|---|---|---|---|')
  meta.steps.forEach((step, idx) => {
    lines.push(`| ${idx + 1} | ${step} | <observed behavior> | <PASS/FAIL/BLOCKED> | <screenshot/video/log link> |`)
  })
  lines.push('')
  lines.push('## Summary Evidence')
  lines.push('')
  lines.push('- UI evidence: `<links/notes>`')
  lines.push('- API/log evidence: `<links/snippets>`')
  lines.push('- Notes: `<key observations>`')
  lines.push('')
  lines.push('## Issues')
  lines.push('')
  lines.push('- `<BUG-ID / N/A>`')
  lines.push('')
  lines.push('## Sign-off')
  lines.push('')
  lines.push('- Product: `<name>`')
  lines.push('- QA: `<name>`')
  lines.push('')
  return lines.join('\n')
}

function buildSsotRow({ scenario, env, tenant, owner, date, result, outPath }) {
  const meta = SCENARIO_META[scenario]
  const fileName = path.basename(outPath)
  const link = `[${fileName}](${outPath})`
  return `| \`${date}\` | ${meta.label} (\`${meta.businessType}\`) | ${env} | \`${tenant}\` | \`${result}\` | ${link} | ${owner} |`
}

function main() {
  const args = parseArgs(process.argv.slice(2))
  if (!SCENARIO_META[args.scenario]) usage(1)
  if (!['staging', 'production'].includes(args.env)) usage(1)
  if (!args.tenant || !args.owner) usage(1)
  if (args.result && !['PASS', 'FAIL', 'BLOCKED', 'IN_PROGRESS'].includes(args.result)) usage(1)

  const date = args.date || todayUtc()
  const scenario = args.scenario
  const env = args.env
  const tenantSlug = safeSlug(args.tenant) || 'tenant'
  const outName = `f7-run-${scenario}-${date}-${env}-${tenantSlug}.md`
  const outPath = path.join(repoRoot, 'docs', 'manual-checklist', outName)

  const content = buildContent({
    scenario,
    env,
    tenant: args.tenant,
    owner: args.owner,
    date,
    result: args.result || 'IN_PROGRESS',
  })

  if (args.dryRun) {
    console.log(`Dry run: ${outPath}`)
    if (args.printSsotRow) {
      const row = buildSsotRow({
        scenario,
        env,
        tenant: args.tenant,
        owner: args.owner,
        date,
        result: args.result || 'IN_PROGRESS',
        outPath,
      })
      console.log('SSOT 10.1 row preview:')
      console.log(row)
    }
    return
  }

  if (fs.existsSync(outPath)) {
    console.error(`File already exists: ${outPath}`)
    process.exit(1)
  }
  fs.writeFileSync(outPath, content, 'utf-8')
  console.log(`Created: ${outPath}`)
  if (args.printSsotRow) {
    const row = buildSsotRow({
      scenario,
      env,
      tenant: args.tenant,
      owner: args.owner,
      date,
      result: args.result || 'IN_PROGRESS',
      outPath,
    })
    console.log('SSOT 10.1 row:')
    console.log(row)
  }
}

main()
