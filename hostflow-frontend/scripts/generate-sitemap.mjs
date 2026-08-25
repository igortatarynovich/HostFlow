import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const DEFAULT_BASE_URL = 'https://hostflow.cc'
const baseUrl = String(process.env.VITE_PUBLIC_BASE_URL || DEFAULT_BASE_URL).trim().replace(/\/+$/, '') || DEFAULT_BASE_URL
const lastmod = new Date().toISOString().slice(0, 10)

const routes = [
  { path: '/', changefreq: 'weekly', priority: '1.0' },
  { path: '/pricing', changefreq: 'weekly', priority: '0.9' },
  { path: '/signup', changefreq: 'weekly', priority: '0.9' },
  { path: '/login', changefreq: 'monthly', priority: '0.6' },
  { path: '/public/intake', changefreq: 'weekly', priority: '0.8' },
  { path: '/public/portal', changefreq: 'monthly', priority: '0.7' },
  { path: '/faq', changefreq: 'weekly', priority: '0.85' },
  { path: '/docs', changefreq: 'weekly', priority: '0.85' },
  { path: '/docs/getting-started', changefreq: 'monthly', priority: '0.75' },
  { path: '/docs/create-company', changefreq: 'monthly', priority: '0.7' },
  { path: '/docs/connect-meta', changefreq: 'monthly', priority: '0.75' },
  { path: '/docs/first-vacancy', changefreq: 'monthly', priority: '0.75' },
  { path: '/docs/first-lead', changefreq: 'monthly', priority: '0.7' },
  { path: '/docs/first-candidate', changefreq: 'monthly', priority: '0.7' },
  { path: '/docs/documents-basics', changefreq: 'monthly', priority: '0.7' },
  { path: '/docs/invite-team', changefreq: 'monthly', priority: '0.65' },
  { path: '/academy', changefreq: 'weekly', priority: '0.8' },
  { path: '/demo', changefreq: 'weekly', priority: '0.85' },
  { path: '/features/candidate-pipeline', changefreq: 'monthly', priority: '0.8' },
  { path: '/features/document-control', changefreq: 'monthly', priority: '0.8' },
  { path: '/features/whatsapp-recruitment', changefreq: 'monthly', priority: '0.8' },
  { path: '/features/meta-ads-recruitment', changefreq: 'monthly', priority: '0.8' },
  { path: '/use-cases/trucking-recruitment', changefreq: 'monthly', priority: '0.8' },
  { path: '/use-cases/high-volume-onboarding', changefreq: 'monthly', priority: '0.8' },
  { path: '/use-cases/recruitment-agencies', changefreq: 'monthly', priority: '0.8' },
  { path: '/use-cases/transport-companies', changefreq: 'monthly', priority: '0.8' },
  { path: '/use-cases/driver-recruitment', changefreq: 'monthly', priority: '0.8' },
  { path: '/use-cases/ats-for-drivers', changefreq: 'monthly', priority: '0.8' },
  { path: '/use-cases/ats-for-transport', changefreq: 'monthly', priority: '0.8' },
  { path: '/use-cases/ats-europe', changefreq: 'monthly', priority: '0.8' },
  { path: '/comparison/hostflow-vs-spreadsheets', changefreq: 'monthly', priority: '0.7' },
  { path: '/comparison/recruitment-crm-vs-ats', changefreq: 'monthly', priority: '0.7' },
  { path: '/legal/terms.html', changefreq: 'yearly', priority: '0.5' },
  { path: '/legal/privacy.html', changefreq: 'yearly', priority: '0.5' },
  { path: '/legal/cookies.html', changefreq: 'yearly', priority: '0.5' },
  { path: '/terms.html', changefreq: 'yearly', priority: '0.4' },
  { path: '/privacy.html', changefreq: 'yearly', priority: '0.4' },
  { path: '/data-deletion.html', changefreq: 'yearly', priority: '0.4' },
]

const xml = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ...routes.map((route) => {
    const loc = `${baseUrl}${route.path}`
    return [
      '  <url>',
      `    <loc>${loc}</loc>`,
      `    <lastmod>${lastmod}</lastmod>`,
      `    <changefreq>${route.changefreq}</changefreq>`,
      `    <priority>${route.priority}</priority>`,
      '  </url>',
    ].join('\n')
  }),
  '</urlset>',
  '',
].join('\n')

const outputPath = resolve(process.cwd(), 'public/sitemap.xml')
writeFileSync(outputPath, xml, 'utf8')
console.log(`[sitemap] generated ${outputPath} (${routes.length} urls)`)
