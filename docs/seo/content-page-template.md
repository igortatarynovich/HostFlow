# SEO Content Page Template (Wave-1)

Use this template for `feature`, `use-case`, and `comparison` pages in `F10`.

## 1) Metadata
- `title`: 50-60 chars, include primary keyword.
- `description`: 140-160 chars, include value proposition + CTA hint.
- `canonical`: final page URL.
- `og:title`, `og:description`, `og:url`, `og:type=website`.

## 2) Above The Fold
- `H1`: primary keyword + clear value.
- 1 short supporting paragraph.
- Primary CTA: `Start free trial` (`/signup`).
- Secondary CTA: `View pricing` (`/pricing`) or `Book demo` (when available).

## 3) Body Structure (H2 Blocks)
- `H2 Problem`: what is broken today.
- `H2 Solution`: how HostFlow solves it.
- `H2 Workflow`: 3-5 concrete steps with outcomes.
- `H2 Proof`: metrics, examples, or operational evidence.
- `H2 Objections`: 2-4 common concerns with short answers.

## 4) Internal Links
- Minimum 3 contextual links:
  - one to a feature page
  - one to a use-case/comparison page
  - one conversion link (`/signup` or `/pricing`)

## 5) FAQ Block
- 3-5 Q/A pairs aligned to long-tail intent.
- Reuse page FAQ in `FAQPage` JSON-LD.

## 6) Schema
- Required: `FAQPage` when FAQ section is present.
- Optional: `SoftwareApplication` when page focuses on product capability.

## 7) Content Constraints
- Paragraphs: 2-4 lines max.
- Lists: use bullets for scannability.
- Avoid generic claims; include operationally verifiable statements.

## 8) Conversion Tracking (minimum)
- Track clicks on primary CTA.
- Track clicks on secondary CTA.
- Track scroll depth milestones (25/50/75/100).
