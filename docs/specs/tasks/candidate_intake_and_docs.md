## Цель проекта

Реализовать полнофункциональный мобильный сканер документов с качеством, аналогичным Scanbot SDK, для использования в анкете кандидата HostFlow. Сканер должен обеспечивать высокое качество сканирования документов, удобный интерфейс и работать полностью офлайн, обеспечивая безопасность и конфиденциальность данных пользователя.

## Основные требования

- 100% офлайн‑работа, без передачи данных на сервер.
- Автоматическая детекция документа в кадре и автоматический захват при оптимальных условиях.
- Warp (выравнивание перспективы) и устранение бликов для получения ровного и читаемого изображения.
- Автофокус, контроль резкости и подсказки пользователю для улучшения качества съёмки.
- Формирование PDF и JPEG файлов с заданным DPI (минимум 300) и необходимыми метаданными.
- Поддержка мобильных браузеров и Progressive Web App (PWA) для удобного использования.
- QR‑handoff с десктопа для быстрого перехода в мобильный сканер.

## Архитектура

1. **Frontend (WebAssembly/PWA)**  
   - Интерфейс сканера реализован на веб-технологиях с использованием WebAssembly для обработки изображений через `opencv.wasm`.  
   - Использование `pdf-lib` для генерации PDF документов.  
   - WebGL применяется для наложения фильтров и улучшения качества изображения в реальном времени.  
   - Вся обработка изображений происходит на клиенте, обеспечивая офлайн‑работу и безопасность.

2. **Backend**  
   - Приём и хранение файлов (при необходимости).  
   - Проверка метаданных документов.  
   - Уведомления и взаимодействие с другими системами HostFlow.  
   - В рамках данного задания основной акцент на frontend, backend описан для полноты архитектуры.

## Технические компоненты

- **Захват камеры**  
  Использование API `getUserMedia` с параметрами:  
  - `ideal: 1920x1080` разрешение  
  - `facingMode: environment` (задняя камера)  
  - `frameRate: 60` кадров в секунду для плавного видео.

- **OpenCV-WASM**  
  - Использовать SIMD‑сборку для ускорения обработки.  
  - Детекция контуров с помощью `cv.findContours`.  
  - Warp с использованием `cv.getPerspectiveTransform` и `cv.warpPerspective` для выравнивания перспективы.  
  - Фильтры: преобразование цвета (`cv.cvtColor`), CLAHE (адаптивное выравнивание контраста), unsharp mask для повышения резкости.

- **WebGL фильтры**  
  Реализация фильтров яркости, контраста, градации серого и резкости для улучшения визуального восприятия.

- **Автофокус и Laplacian‑метрика**  
  - Использование вариации Laplacian (variance) для оценки резкости кадра.  
  - Порог резкости: variance > 120 считается резким кадром.

- **Glare detection (обнаружение бликов)**  
  - Анализ соотношения ярких пикселей в кадре.  
  - Если доля ярких пикселей > 0.03, выводится предупреждение пользователю.

- **Стабилизация рамки**  
  - Применение экспоненциального скользящего среднего (EMA) для сглаживания координат рамки: `lerp(prevQuad, newQuad, 0.2)`.

- **Авто‑захват**  
  - Автоматическое снятие кадра при стабильности рамки > 0.8 и удовлетворительной резкости (Laplacian ok).

- **PDF‑генерация**  
  - Использование `pdf-lib` для генерации PDF.  
  - Поддержка DPI 300.  
  - Форматы страниц: ID (85.6×54 мм) и A4 (210×297 мм).

- **PWA‑режим**  
  - Наличие `manifest.json` для установки приложения.  
  - `service worker` для офлайн‑кэширования и повышения производительности.

## UI/UX спецификация

- Полноэкранный режим с затемнённым фоном для концентрации пользователя на документе.  
- Рамка для документа с подсказками по положению и ориентации.  
- Индикатор прогресса заполнения кадра (от 0 до 100 %).  
- Интерактивные подсказки: «Поднесите ближе», «Держите ровно», «Устраните блики» и др.  
- Кнопки управления: `Снять страницу`, `Закрыть сканер`, `Переключить фильтр`.  
- Превью после съёмки с возможностью переключения фильтров и подтверждения снимка.  
- Возможность перехода на следующую страницу документа для многостраничных сканов.  
- Поддержка локализации на польский (PL), английский (EN) и русский (RU) языки.

## Алгоритмы качества

- Детекция 4‑угольника с помощью `cv.approxPolyDP` для определения контура документа.  
- Warp изображения по найденным углам для получения нормализованного прямоугольника.  
- Применение CLAHE и adaptive threshold для повышения контраста и читаемости.  
- Сравнение Laplacian метрик для определения оптимального момента авто‑захвата.  
- Проверка бликов с помощью вычисления `glareRatio` и информирование пользователя.

## Безопасность и производительность

- Все операции выполняются локально, без отправки изображений на сервер.  
- Использование `createImageBitmap` и `OffscreenCanvas` для эффективного рендера и обработки изображений.  
- Целевое время обработки кадра ≤ 150 мс на средних мобильных устройствах.  
- Ограничение использования памяти до ≤ 100 MB для стабильной работы.

## Тест‑план

- Тестовые сценарии для сканирования ID-карт, паспортов и документов формата A4.  
- Проверка корректности авто‑детекции контура документа, warp, фильтров и CLAHE.  
- Верификация качества PDF‑выхода с правильными размерами и DPI.  
- Тестирование офлайн‑режима и функционала QR‑handoff для перехода с десктопа на мобильное устройство.


## Definition of Done

- Авто‑захват, warp, CLAHE, генерация PDF, UI‑подсказки и офлайн‑режим успешно работают в мобильных браузерах iOS и Android.  
- Качество изображения соответствует минимум 300 DPI.  
- Тесты резкости и контраста проходят не менее чем на 95 % примеров.

## Референсы и источники (читать обязательно)

**Основы и API**
- OpenCV.js (официальная дока): https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html
- Туториал по сканеру документов (OpenCV/Canny/Contours/Warp): https://codelabs.developers.google.com/codelabs/opencv-doc-scanner
- pdf-lib (создание PDF в браузере): https://pdf-lib.js.org/docs/api/classes/pdfdocument
- MDN getUserMedia (камеры и констрейнты): https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
- WebGL (фрагментные шейдеры): https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/Tutorial/Shader_programs
- PWA (Manifest + ServiceWorker): https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps

**Опорные open‑source реализации**
- DocumentScanner (JS+OpenCV): https://github.com/AmruthPillai/DocumentScanner
- AidanCasey/document-scanner (TypeScript): https://github.com/AidanCasey/document-scanner
- photo-to-scan (канвас фильтры): https://github.com/raghavk16/photo-to-scan

> Эти ссылки приведены как ориентиры алгоритмов и API. Копипаст не допускается, но логика совпадает с тем, что требуется.

---

## Сниппеты (готовые фрагменты для встраивания)

### 1) Констрейнты камеры (1080p, задняя, 60 fps)
```ts
const stream = await navigator.mediaDevices.getUserMedia({
  video: {
    width: { ideal: 1920 },
    height: { ideal: 1080 },
    frameRate: { ideal: 60 },
    facingMode: { ideal: 'environment' }
  },
  audio: false
});
video.srcObject = stream;
await video.play();
```

### 2) Выбор лучшего внешнего четырёхугольника (контур документа)
```ts
function chooseBestQuad(contours: cv.MatVector, W: number, H: number, preset: 'id'|'pass'|'a4') {
  const frameArea = W*H;
  const aspTarget = preset==='id' ? 85.6/54 : preset==='pass' ? 125/88 : 210/297;
  let best: {approx: cv.Mat, area: number, rect: any, aspect: number} | null = null;
  for (let i=0;i<contours.size();i++) {
    const c = contours.get(i);
    const peri = cv.arcLength(c, true);
    const approx = new cv.Mat();
    cv.approxPolyDP(c, approx, 0.02*peri, true);
    if (approx.rows !== 4 || !cv.isContourConvex(approx)) { approx.delete(); continue; }
    const area = Math.abs(cv.contourArea(approx));
    if (area/frameArea < 0.45) { approx.delete(); continue; }
    const rect = cv.boundingRect(approx);
    const rectangularity = area / (rect.width*rect.height);
    if (rectangularity < 0.85) { approx.delete(); continue; }
    const aspect = rect.width/rect.height;
    if (Math.abs(aspect-aspTarget) > aspTarget*0.08) { approx.delete(); continue; }
    const pts = approx.data32S;
    const nearEdge = (x:number,y:number) => (x<W*0.10 || x>W*0.90 || y<H*0.10 || y>H*0.90);
    const edgeHits = [0,2,4,6].filter(k => nearEdge(pts[k], pts[k+1])).length;
    if (edgeHits < 2) { approx.delete(); continue; }
    if (!best || area > best.area) best = { approx, area, rect, aspect }; else approx.delete();
  }
  return best?.approx || null;
}
```

### 3) Перспективное выравнивание (warp)
```ts
function warpToPreset(srcMat: cv.Mat, quad: cv.Mat, outW: number, outH: number) {
  const dst = new cv.Mat();
  const srcTri = cv.matFromArray(4,1,cv.CV_32FC2,[
    quad.data32S[0], quad.data32S[1],
    quad.data32S[2], quad.data32S[3],
    quad.data32S[4], quad.data32S[5],
    quad.data32S[6], quad.data32S[7]
  ]);
  const dstTri = cv.matFromArray(4,1,cv.CV_32FC2,[ 0,0, outW,0, outW,outH, 0,outH ]);
  const M = cv.getPerspectiveTransform(srcTri, dstTri);
  cv.warpPerspective(srcMat, dst, M, new cv.Size(outW,outH), cv.INTER_LINEAR, cv.BORDER_REPLICATE, new cv.Scalar());
  srcTri.delete(); dstTri.delete(); M.delete();
  return dst;
}
```

### 4) Метрики качества (Laplacian, glare, fill)
```ts
function laplacianVariance(gray: cv.Mat): number {
  const lap = new cv.Mat();
  cv.Laplacian(gray, lap, cv.CV_64F);
  const mean = new cv.Mat(); const std = new cv.Mat();
  cv.meanStdDev(lap, mean, std);
  const v = std.doubleAt(0,0)**2; lap.delete(); mean.delete(); std.delete();
  return v;
}
function glareRatio(gray: cv.Mat): number {
  const thr = new cv.Mat();
  cv.threshold(gray, thr, 235, 255, cv.THRESH_BINARY);
  const white = cv.countNonZero(thr);
  const ratio = white / (gray.rows * gray.cols);
  thr.delete(); return ratio;
}
function fillRatio(quad: cv.Mat, W:number, H:number): number {
  const area = Math.abs(cv.contourArea(quad));
  return area/(W*H);
}
```

### 5) Сглаживание и автоспуск
```ts
function lerp(a:number,b:number,t:number){return a+(b-a)*t}
function smoothQuad(prev:number[], next:number[], t=0.2){
  return prev.map((v,i)=>lerp(v,next[i],t));
}
class Stability {
  buf: {t:number, fill:number, sharp:number, glare:number, jitter:number}[]=[];
  push(m:{fill:number,sharp:number,glare:number,jitter:number}){
    const t=performance.now(); this.buf.push({t,...m});
    while (this.buf.length && t-this.buf[0].t>800) this.buf.shift();
  }
  ok(th={fill:.7, sharp:120, glare:.15, jitter:2}){
    const win=this.buf.filter(x=>this.buf[this.buf.length-1].t-x.t<=600);
    if(win.length<6) return false;
    return win.every(x=>x.fill>=th.fill && x.sharp>=th.sharp && x.glare<=th.glare && x.jitter<=th.jitter);
  }
}
```

### 6) Шейдер WebGL (grayscale + контраст)
```glsl
precision mediump float;
varying vec2 vUv; uniform sampler2D tex; uniform float contrast; // 1.0..2.0
void main(){
  vec4 c = texture2D(tex, vUv);
  float g = dot(c.rgb, vec3(0.2126,0.7152,0.0722));
  g = (g-0.5)*contrast + 0.5; g = clamp(g,0.0,1.0);
  gl_FragColor = vec4(vec3(g),1.0);
}
```

### 7) Сборка PDF (pdf-lib, 300 DPI)
```ts
import { PDFDocument, StandardFonts } from 'pdf-lib';
async function pagesToPdf(pages: Blob[], mm:{w:number,h:number}){
  const pdf = await PDFDocument.create();
  const DPI = 300; const ptPerInch = 72; const mmPerInch = 25.4;
  const widthPt = (mm.w/mmPerInch)*ptPerInch; const heightPt = (mm.h/mmPerInch)*ptPerInch;
  for (const blob of pages){
    const bytes = new Uint8Array(await blob.arrayBuffer());
    const img = await pdf.embedJpg(bytes);
    const page = pdf.addPage([widthPt, heightPt]);
    page.drawImage(img, { x:0, y:0, width: widthPt, height: heightPt });
  }
  const out = await pdf.save();
  return new Blob([out], { type: 'application/pdf' });
}
```

### 8) PWA Service Worker (no‑store для index.html, кэш ассетов)
```js
self.addEventListener('install', (e)=>{ self.skipWaiting(); });
self.addEventListener('activate', (e)=>{ clients.claim(); });
// Статические ассеты с хэшами — immutable, index.html — не кэшируем на долго
```

---

## UI‑гайд (скрин‑потоки и тексты)

1) **Экран сканера**: полноэкранный; полупрозрачная маска; подсказка‑чип: «Поднесите ближе…», «Держите ровно…», «Уберите блики…»; индикатор прогресса 0–100 %.
2) **Автоспуск**: когда метрики в норме ≥600 мс → анимация захвата.
3) **Превью страницы**: только результат `warp`; кнопки: «Переснять», «Фильтры: Ч/Б, Чистый фон, Оригинал», «Добавить страницу/Далее».
4) **Многостраничный режим**: pager 1…N, возможность переснять любую страницу.
5) **Завершение**: генерация PDF, отправка; показываем размер, страницы, тип документа.
6) **Debug‑панель (скрытая, 5 тапов по заголовку)**: fps, laplacian, glare, fill, jitter, size, preset; toggle «show contours».

Тексты i18n ключами: `scanner.place_in_frame`, `scanner.too_bright`, `scanner.too_blurry`, `scanner.auto_snap`, `scanner.progress` и т.д.

---

## Пороговые значения (боевые)

| Пресет | fill_ratio | Laplacian (sharp) | glare | aspect tolerance |
|---|---:|---:|---:|---:|
| id_card | ≥ 0.70 | ≥ 120 | ≤ 0.15 | ±8% |
| passport | ≥ 0.70 | ≥ 120 | ≤ 0.15 | ±8% |
| A4 | ≥ 0.80 | ≥ 140 | ≤ 0.12 | ±5% |

Если пороги не достигнуты — показываем конкретную подсказку и запрещаем авто‑спуск.

---

## Интеграция с HostFlow

- `required_files.frame.preset` ∈ `id_card|passport|a4` управляет размерами `warp` и порогами.
- `type: sides|paged` задаёт сценарий: 2 стороны (front/back) или N страниц.
- Загрузка: сначала S3 presigned upload → затем `POST /documents/commit` с метаданными (страницами/стороной/мим-типом).
- На ПК показывать QR‑handoff: `/public/scan?session=...`.

---

## Тест‑кейсы (приёмка)

1) **ID**: дневной свет, стол без рисунка. Автоспуск ≤2 c, прогресс ≥95 %, PDF 300 DPI, пороги пройдены.
2) **Паспорт**: 8–12 страниц, возможность переснять отдельную страницу; итоговый PDF ≤30 MB.
3) **A4**: лампа, без бликов; warp ровный, текст читаем.
4) **iOS Safari**: `<input capture>` отдает оригинальный Blob; ориентация/EXIF корректные.
5) **Офлайн**: перезагрузка PWA в авиарежиме — сканер работает, файлы копятся в IndexedDB; при появлении сети — догружаются.

---

## Частые ошибки и как проверять

- `canvas` рендерится в CSS‑размере, а не в реальном DPI → фикс: `width/height` в пикселях устройства.
- В стейт кладётся «сырое фото» вместо `warp` → запретить этот путь; превью/загрузка только `warp`‑результат.
- Фильтры крутятся в main‑thread → перенос в Web Worker/WebGL.
- Автоспуск без стабильности → добавить буфер кадров и проверку `ok()`.
- Service Worker кэширует `index.html` → ставим `no-store` и версионирование.

---

## Definition of Done (дополнение, финальная проверка)

- На Android (Chrome) и iOS (Safari) автодетекция+автоспуск работают стабильно (не менее 20 успешных сессий подряд на разных фонах).
- В debug‑логах среднее время обработки кадра ≤ 60 мс, FPS предпросмотра ≥ 20.
- Все PDF формируются с корректными физическими размерами (ID 85.6×54 мм, A4 210×297 мм) и читаются в любом.viewer.
- Никаких «полных фото кадра» в пайплайне — только результат `warp`.
- Все строки UI проходят i18n (PL/EN/RU), включая подсказки качества.
