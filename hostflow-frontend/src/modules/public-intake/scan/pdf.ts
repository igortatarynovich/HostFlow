import type { ScanPresetKey } from './analyzer'
import { getPresetSpec } from './presets'

export type PdfPageInput = {
  bytes: Uint8Array
  widthPx: number
  heightPx: number
  preset: ScanPresetKey
}

const mmToPt = (mm: number) => (mm / 25.4) * 72

type PdfObject = {
  id: number
  parts: Array<string | Uint8Array>
}

export async function buildPdfDocument(pages: PdfPageInput[]): Promise<Uint8Array> {
  if (pages.length === 0) {
    throw new Error('pdf_no_pages')
  }

  const objects: PdfObject[] = []
  const addObject = (parts: Array<string | Uint8Array>): number => {
    const id = objects.length + 1
    objects.push({ id, parts })
    return id
  }

  const pageRefs: number[] = []
  const imageNameForIndex = (index: number) => `/Im${index + 1}`

  // reserve pages tree; we will fill after pages are known
  const pagesTreeId = addObject(['']) // placeholder

  pages.forEach((page, index) => {
    const presetSpec = getPresetSpec(page.preset)
    const pageWidthPt = mmToPt(presetSpec.widthMm)
    const pageHeightPt = mmToPt(presetSpec.heightMm)
    const imageObjId = addObject([
      `<< /Type /XObject /Subtype /Image /Width ${page.widthPx} /Height ${page.heightPx} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${page.bytes.length} >>\n`,
      'stream\n',
      page.bytes,
      '\nendstream\n',
    ])

    const imgName = imageNameForIndex(index)
    const imageRatio = page.widthPx / page.heightPx
    const pageRatio = pageWidthPt / pageHeightPt
    let drawWidth = pageWidthPt
    let drawHeight = pageHeightPt
    if (imageRatio > pageRatio) {
      drawHeight = drawWidth / imageRatio
    } else {
      drawWidth = drawHeight * imageRatio
    }
    const offsetX = (pageWidthPt - drawWidth) / 2
    const offsetY = (pageHeightPt - drawHeight) / 2
    const contentStream = `q ${drawWidth.toFixed(2)} 0 0 ${drawHeight.toFixed(2)} ${offsetX.toFixed(
      2,
    )} ${offsetY.toFixed(2)} cm ${imgName} Do Q\n`
    const contentBytes = new TextEncoder().encode(contentStream)
    const contentId = addObject([
      `<< /Length ${contentBytes.length} >>\n`,
      'stream\n',
      contentBytes,
      '\nendstream\n',
    ])
    const pageId = addObject([
      `<< /Type /Page /Parent ${pagesTreeId} 0 R /Resources << /XObject << ${imgName} ${imageObjId} 0 R >> >> /MediaBox [0 0 ${pageWidthPt.toFixed(
        2,
      )} ${pageHeightPt.toFixed(2)}] /Contents ${contentId} 0 R >>\n`,
    ])
    pageRefs.push(pageId)
  })

  const kids = pageRefs.map((id) => `${id} 0 R`).join(' ')
  const pagesTree = `<< /Type /Pages /Count ${pageRefs.length} /Kids [${kids}] >>\n`
  objects[pagesTreeId - 1].parts = [pagesTree]

  const catalogId = addObject([`<< /Type /Catalog /Pages ${pagesTreeId} 0 R >>\n`])

  return serializePdf(objects, catalogId)
}

function serializePdf(objects: PdfObject[], catalogId: number): Uint8Array {
  const encoder = new TextEncoder()
  const chunks: Uint8Array[] = []
  const offsets: number[] = new Array(objects.length + 1).fill(0)
  let position = 0

  const writeText = (text: string) => {
    const data = encoder.encode(text)
    chunks.push(data)
    position += data.length
  }

  const writeBinary = (data: Uint8Array) => {
    chunks.push(data)
    position += data.length
  }

  writeText('%PDF-1.4\n')
  objects.forEach((obj) => {
    offsets[obj.id] = position
    writeText(`${obj.id} 0 obj\n`)
    obj.parts.forEach((part) => {
      if (typeof part === 'string') {
        writeText(part)
      } else {
        writeBinary(part)
      }
    })
    writeText('endobj\n')
  })

  const xrefStart = position
  writeText(`xref\n0 ${objects.length + 1}\n`)
  writeText('0000000000 65535 f \n')
  for (let i = 1; i <= objects.length; i += 1) {
    const offset = offsets[i] ?? 0
    writeText(`${offset.toString().padStart(10, '0')} 00000 n \n`)
  }
  writeText('trailer\n')
  writeText(`<< /Size ${objects.length + 1} /Root ${catalogId} 0 R >>\n`)
  writeText('startxref\n')
  writeText(`${xrefStart}\n`)
  writeText('%%EOF')

  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const output = new Uint8Array(total)
  let offset = 0
  chunks.forEach((chunk) => {
    output.set(chunk, offset)
    offset += chunk.length
  })
  return output
}
