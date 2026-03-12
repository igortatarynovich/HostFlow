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
