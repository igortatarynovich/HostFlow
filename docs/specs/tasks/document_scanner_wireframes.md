## Document Scanner UX — Wireframes & Copy

### 1. Screen Inventory
1. **Session bootstrap**
   - URL: `/public/scan?token=<token>&doc=<code>[&session=<id>]`
   - States:
     1. Loading preset/session.
     2. Error (invalid token, expired session).
     3. Permissions prompt (camera required).
2. **Capture wizard**
   - Header with doc name, company logo (optional), “Need help?” link.
   - Main area split vertically:
     - Left: camera viewport + overlay.
     - Right (or bottom on mobile): step instructions, capture controls, progress indicators.
3. **Preview modal**
   - After capture, show still image with applied crop.
   - Buttons: `Use photo`, `Retake`.
4. **Captured pages drawer**
   - Persistent list of steps with thumbnails, statuses, action chips (`Retake`, `Delete`).
5. **Processing screen**
   - Shows spinner per page + overall progress.
   - Includes ability to stay on page while backend finishes.
6. **Success / next steps**
   - Confirmation card: “Photos submitted for review”.
   - CTA back to application or close tab.

### 2. Layout Sketches (textual)
```
┌──────────────────────────────────────────────────────────────────────┐
│ Heading: “Scan Tachograph Card”                             Step 1/2 │
│ Subtext: “Place the document inside the frame and avoid glare.”      │
├──────────────────────┬───────────────────────────────────────────────┤
│ [ Live camera feed ] │  [ Instruction card ]                         │
│  + aspect overlay    │  Title: “Front side”                          │
│  + contour guide     │  Tips (bullet list)                           │
│                      │  Badges: light, rotation, stability indicator │
│ [ Capture button ]   │  Actions:                                     │
│ [ Retake ] [ Torch ] │    • Capture photo (primary)                  │
│ [ Upload from files] │    • Upload existing photo                    │
└──────────────────────┴───────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────┐
│ Captured pages                                                      ▼ │
│ ┌──────────┬──────────────┬──────────┐  ┌──────────┬───────────────┐  │
│ │ Thumb    │ Front side   │ READY    │  │ Thumb    │ Back side     │  │
│ │          │ 0.9 MB       │          │  │          │ WAITING       │  │
│ │          │ Updated now  │ [Retake] │  │          │               │  │
│ └──────────┴──────────────┴──────────┘  └──────────┴───────────────┘  │
│ [ Submit document ] (disabled until all required steps READY)         │
└──────────────────────────────────────────────────────────────────────┘
```

### 3. Step Definitions & Copy
| Preset code | Steps | Heading / Instruction text | Tips (bullet points) |
|-------------|-------|----------------------------|----------------------|
| `id_card` / `driver_license` / `tacho_card` | 1. Front<br>2. Back | - Step title: “Front side of ID card” / “Back side…”<br>- Subtitle: “Align the card with the frame. Avoid glare.” | - “Fill the frame edge-to-edge.”<br>- “Hold the phone steady for 2 seconds.”<br>- “Turn off flash if you see reflections.” |
| `passport_main` | 1. Data spread | - Heading: “Passport spread with photo” | - “Keep both pages in view.”<br>- “Lay passport flat on a dark surface.” |
| `passport_all_pages` | 1. Extra page loop (repeatable) | - Heading: “Additional page {n}” | - “Photograph remaining pages with stamps or visas.”<br>- “Use ‘Skip page’ if none left.” |
| `residence_permit` (new) | 1. Front<br>2. Back<br>3. Registration stamp (optional) | - Third step flagged as optional; UI shows badge “Optional”. | - “Add this if your card has a registration mark.” |

### 4. Camera Interaction States
1. **Permission pending**
   - Full-height card with illustration + CTA “Allow camera”.
   - Secondary link “Upload files instead” (opens fallback).
2. **Permission denied**
   - Show instructions to enable camera in browser settings + persistent fallback button.
3. **Active capture**
   - Buttons: `Capture` (primary), `Retake` (secondary), `Torch` (if supported), `Switch camera`.
   - Stability indicator: dot turning green when average motion < threshold for 0.5s.
4. **Processing upload**
   - On `Use photo`, show inline progress bar inside step card.

### 5. Fallback Upload UX
- Same wizard, but capture pane replaces `<video>` with drag-and-drop area.
- Buttons: `Upload from device`, `Paste from clipboard`.
- After selecting file, the same preview modal appears.
- Steps still enforce order/progress; retake simply reopens file picker.

### 6. Microcopy Summary
```
public.scan.heading                = {docTitle}
public.scan.steps.progress         = Step {current} of {total}
public.scan.capture.cta            = Capture photo
public.scan.capture.cta_fallback   = Upload from device
public.scan.capture.preview_use    = Use this photo
public.scan.capture.preview_retake = Retake
public.scan.capture.permission     = Allow camera access to continue
public.scan.capture.permission_help= Enable camera in browser settings or upload files instead.
public.scan.review.submit          = Submit document
public.scan.review.submit_disabled = Complete all pages to continue
public.scan.review.processing      = Processing {done}/{total} pages…
public.scan.review.success_title   = Files sent for review
public.scan.review.success_body    = You can close this tab. HR will notify you if anything else is needed.
```

### 7. Open Points for Design
- Choose actual color scheme for overlays (brand teal vs warning).
- Decide whether progress lives at top bar or inside camera pane.
- Animations for contour detection placeholder (pulsing frame vs dashed line).
- Illustration assets for permission/error states.
