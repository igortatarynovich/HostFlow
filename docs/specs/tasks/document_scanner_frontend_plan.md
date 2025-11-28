## Document Scanner Redesign — Frontend & UX Plan

### 1. Goals (from stakeholder brief)
- Full-screen scanner wizard with camera-first UX, not just `<input type="file">`.
- Per-document presets define steps (pages, hints, completion rules).
- Always guide the candidate: current step, instructions, progress, what happens next.
- Allow auto-detect/cropping overlay (initially visualization, later powered by OpenCV).
- Support both mobile (camera) and desktop (fallback upload) without breaking the flow.

### 2. Desired User Journey (per session)
1. **Entry**
   - URL contains `token`, `doc`, optional `session`.
   - Fetch preset metadata → show hero card with doc name, number of steps, estimated time.
   - Prompt for camera permission immediately (if denied, surface fallback instructions).
2. **Capture loop**
   - For each preset step:
     - Heading (e.g., “Step 1 of 2 · Front side of ID”).
     - Tips block (“Fill the frame, avoid glare”).
     - Live camera preview (`<video>` fed by `getUserMedia`). Overlay aspect-ratio frame + animated contour.
     - Controls: `Retake`, `Use photo`, `Torch` (if supported), `Switch camera` (if device exposes multiple).
     - When user hits “Use photo”:
       - Grab frame from `<canvas>`, optionally apply client-side crop (basic contour detection fallback: CSS perspective).
       - Show review modal/preview; user can confirm or retake.
       - On confirm → upload to backend `/public/scan-sessions/{id}/pages`.
   - If camera unavailable/refused:
     - Show same step UI but primary button opens hidden `<input type="file">`.
     - Selected file is previewed in the same review modal.
3. **Captured pages list**
   - Sticky drawer / bottom sheet listing each step with thumbnail, status, controls:
     - `Ready`, `Needs upload`, `Processing`, `Error`.
     - Actions: `Retake` (jumps back to that step), `Delete`.
4. **Completion**
   - “Submit document” button enabled only when every required step is `Ready`.
   - On click, call `POST /public/scan-sessions/{id}/process`, show spinner + progress.
   - Success screen summarizing statuses and what happens next.

### 3. Frontend Technical Plan
1. **State machine**
   - Introduce `ScannerSessionStore` (Zustand or Redux slice already used) with:
     - `sessionId`, `currentStepIndex`, `steps[]` (code, title, status, thumbnail, fileRef).
     - `deviceCapabilities` (camera supported, facing modes).
     - Actions: `initFromPreset`, `setStepStatus`, `captureFrame`, `uploadStep`, `retakeStep`, `processSession`.
   - Provide selectors for UI components (wizard header, camera pane, queue list).
2. **Camera component**
   - Build `CameraPane`:
     - Handles `navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })`.
     - Displays `<video>` + `<canvas>` overlay; supports `requestVideoFrameCallback` for future auto-detect.
     - Fallback button toggles hidden file input.
     - Expose `capture()` method returning `Blob` + metadata.
   - Manage permission states: `pending`, `granted`, `denied`, `unsupported`.
3. **Step controller**
   - `ScannerWizard` orchestrates steps:
     - Renders current step info.
     - Hooks into `CameraPane` for capture.
     - On confirm, pushes file to queue + calls backend upload (with progress indicator).
4. **Auto-detect overlay (phase 1 placeholder)**
   - Implement purely visual overlay showing expected aspect ratio + “stability” indicator (e.g., color change when deviation < threshold).
   - Provide hook for future integration with WebAssembly/OpenCV when ready.
5. **Uploads & processing**
   - Keep existing REST calls but restructure to support per-step metadata (`page_index`, `manual_crop` flags).
   - Display upload progress per step, disable navigation until request resolves or fails.
6. **Desktop fallback**
   - Detect absence of `mediaDevices` or permission denial → automatically switch to file-upload mode but keep same step-by-step UI.

### 4. Backend Considerations
- Existing endpoints continue to work; only adjustment is optional metadata structure (`meta.manual`, `capture_mode`).
- Optionally add `POST /public/scan-sessions/{id}/pages/batch` if we switch to buffered uploads later (not required for phase 1).
- Ensure CORS allows camera usage over HTTPS (already in place).

### 5. Implementation Milestones
| Sprint | Deliverable | Notes |
|-------|-------------|-------|
| 0 | UX mockups + preset copy deck | Needed for localizations and guidance text. |
| 1 | CameraPane component + permission handling + fallback upload | Basic capture + preview without backend. |
| 2 | Step controller + integration with presets + session API | Sequential steps, upload per step, thumbnails. |
| 3 | Submission flow + progress + error handling | “Submit/Process” gating, summary screen. |
| 4 | Visual overlays + stability indicator | Optional auto-detect visualization. |
| 5 | Polish: responsive layout, accessibility, localization, analytics events. |

### 6. Acceptance Criteria
- Candidate can complete entire document flow on mobile (camera) and desktop (file upload).
- UI always indicates current step and remaining steps.
- Each captured page visible with thumbnail + status + retake.
- “Submit” disabled until all required steps satisfied.
- No blocking reliance on `<input type="file">`; camera-first UX works on Chrome/Safari latest.

### 7. Open Questions / Follow-ups
- Do we need offline caching (PWA) for low connectivity?
- Should we store local backups before upload completes?
- When OpenCV-in-browser becomes available, we’ll swap visual overlay with actual contour detection; need API contract for sending auto-crop coordinates.
