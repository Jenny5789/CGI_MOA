/* 합성하기: 단계별 안내 화면
   1 상의 사진 고르기 -> 2 인물 사진 고르기
   -> 3 점 찍어 상의 추출 -> 확인 -> 다듬기 팝업(브러시, 지우개) -> 완료
   -> 4 점 찍어 입힐 영역 추출 -> 확인 -> 다듬기 팝업(브러시, 지우개) -> 다음 -> 합성 설정 팝업(체크 두 개) -> 합성 시작
   -> 결과, 저장
   오른쪽 "내 작업 기록"은 저장 여부와 관계없이 합성한 결과 전체(명세 6-1)를 보여 준다. 저장하지 않은 결과는 24시간 뒤 서버에서 삭제된다.
   서버 연결 (src/api/studio.js)
   - 1·2단계: 고른 사진을 서버에 올린다(명세 3-1)
   - 3단계: 점만 찍어 둔다. "확인"을 누르면 서버 SAM2로 실제 윤곽을 받아 다듬기 팝업을 연다(4-1)
   - 4단계: 3단계와 같이 인물 사진에 점을 찍고 "확인"을 누르면 SAM2로 지금 입은 상의 영역을 받아 다듬기 팝업을 연다(4-1).
     "합성 시작"에서 서버 AnyDoor 합성 요청 → 2초마다 진행 확인 → 결과(5-1~5-3)
   - 결과 "저장": 서버에 저장 표시(6-2)
   아직 서버에 안 가는 것: 다듬기 팝업에서 고친 상의 윤곽(서버는 SAM2 윤곽으로 합성), 합성 설정 체크 두 개(opts) */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import studioCss from '../styles/studio-guide.css?inline';
import usePageStyle from '../components/usePageStyle.js';
import useToast from '../components/useToast.js';
import TopNav from '../components/TopNav.jsx';
import {
  boxFit, drawContain, drawCover, drawDot, fly, loadImage, makeWork, maskBBox, newCanvas, pointer,
} from '../studio/canvas.js';
import MaskEditor from '../studio/MaskEditor.jsx';
import { listResults, updateResult } from '../api/results.js';
import { extractGarment, getJob, getResult, requestCompose, uploadImage } from '../api/studio.js';
import { formatKoreanDate } from '../utils/date.js';

// 이 화면은 body 아래가 세로로 꽉 차는 구조라서 React가 끼워 넣은 #root 칸도 같은 모양으로 맞춘다
const ROOT_CSS = '\n#root { height: 100%; display: flex; flex-direction: column; min-height: 0; }\n'
  + '@media (max-width: 1100px) { #root { height: auto; display: block; } }\n';
const PAGE_CSS = studioCss + ROOT_CSS;

const SAMPLES = {
  1: ['/assets/gallery/AutumnWarm_Male.jpg', '/assets/gallery/SpringWarm_Female.jpg', '/assets/gallery/SummerCool_Female.jpg'],
  2: ['/assets/samples/sample-object-person.jpg', '/assets/gallery/girl_Santorini.jpg', '/assets/gallery/Paris_Female.jpg'],
};

const STEPS = [
  { n: 1, label: '상의 사진' },
  { n: 2, label: '인물 사진' },
  { n: 3, label: '상의 영역' },
  { n: 4, label: '합성 영역' },
];

const SLOTS = [
  { n: 1, name: '상의 사진', empty: '옷 사진 또는 착용 사진' },
  { n: 2, name: '인물 사진', empty: '선택 전' },
  { n: 3, name: '지정한 상의', empty: '지정 전' },
];

const PICK_TEXT = {
  1: { title: '1. 상의 사진 선택', helpTitle: '사용할 수 있는 사진', help: <>옷만 찍은 사진, 사람이 입은 사진 모두 사용할 수 있습니다.</> },
  2: { title: '2. 인물 사진 선택', helpTitle: '권장 사진', help: <>상의를 입힐 <em>인물</em>의 사진을 선택합니다.<br />상반신이 잘 보이는 사진을 권장합니다.</> },
};

// 버튼 상태가 그대로면 화면을 다시 그리지 않는다 (브러시로 칠하는 동안 매번 다시 그리는 것을 막음)
const sameUi = (a, b) => Object.keys(b).every((k) => a[k] === b[k]);

const PANEL_KEYS ={ left: 'moa_panel_left', right: 'moa_panel_right' };
const readPanel = (side) => {
  try { return localStorage.getItem(PANEL_KEYS[side]) === 'closed' ? 'closed' : 'open'; } catch { return 'open'; }
};
const writePanel = (side, v) => { try { localStorage.setItem(PANEL_KEYS[side], v); } catch { /* 저장 불가 시 무시 */ } };

const ArrowIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
);
const UploadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 16V4" /><path d="M7 9l5-5 5 5" /><path d="M4 20h16" /></svg>
);

// 캔버스에 한 번 그려 두는 작은 그림 (추출한 상의 칸, 작업 기록 썸네일). source가 바뀔 때만 다시 그린다.
function DrawnCanvas({ width, height, source, draw }) {
  const ref = useRef(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { draw(ref.current.getContext('2d'), source); }, [source]);
  return <canvas ref={ref} width={width} height={height} />;
}

const drawCutoutThumb = (ctx, { canvas, bbox }) => {
  ctx.clearRect(0, 0, 480, 300);
  drawContain(ctx, canvas, bbox.x, bbox.y, bbox.w, bbox.h, 480, 300);
};
const drawHistThumb = (ctx, canvas) => drawCover(ctx, canvas, 0, 0, canvas.width, canvas.height, 400, 300);

// 서버가 준 흑백 윤곽 PNG(상의 흰색)를 화면용 윤곽(상의 부분만 불투명한 흰색, 나머지 투명)으로 바꾼다. 크기는 작업용 사본(w, h)에 맞춘다
const maskFromUrl = async (url, w, h) => {
  const img = await loadImage(url);
  const c = newCanvas(w, h);
  const ctx = c.getContext('2d');
  ctx.drawImage(img, 0, 0, w, h);
  const d = ctx.getImageData(0, 0, w, h);
  for (let i = 0; i < d.data.length; i += 4) {
    const on = d.data[i] > 127;
    d.data[i] = 255; d.data[i + 1] = 255; d.data[i + 2] = 255;
    d.data[i + 3] = on ? 255 : 0;
  }
  ctx.putImageData(d, 0, 0);
  return c;
};

// 화면용 영역(칠한 곳만 불투명)을 서버에 보낼 흑백 PNG(칠한 곳 흰색, 나머지 검정)로 바꾼다 (명세 5-1 area_mask)
const areaMaskBlob = (mask) => new Promise((resolve) => {
  const { width: w, height: h } = mask;
  const c = newCanvas(w, h);
  const ctx = c.getContext('2d');
  ctx.drawImage(mask, 0, 0);
  const d = ctx.getImageData(0, 0, w, h);
  for (let i = 0; i < d.data.length; i += 4) {
    const v = d.data[i + 3] > 0 ? 255 : 0;
    d.data[i] = v; d.data[i + 1] = v; d.data[i + 2] = v; d.data[i + 3] = 255;
  }
  ctx.putImageData(d, 0, 0);
  c.toBlob(resolve, 'image/png');
});

// 합성 작업이 끝날 때까지 2초마다 진행을 확인한다 (명세 5-2). 끝나면 결과 번호를 돌려준다
const JOB_POLL_MS = 2000;
const waitForJob = async (jobId, onProgress) => {
  for (;;) {
    const job = await getJob(jobId);
    onProgress(job);
    if (job.status === 'done') return job.result_id;
    if (job.status === 'failed') throw new Error((job.error && job.error.message) || '합성에 실패했습니다');
    await new Promise((r) => setTimeout(r, JOB_POLL_MS));
  }
};

export default function Studio() {
  usePageStyle(PAGE_CSS, 'MOA — 합성하기');
  const [toast, showToast] = useToast(2000);

  /* ---------- 화면 상태 ---------- */
  const [step, setStep] = useState(0); // 0 시작, 1~4 단계, 'result' 결과
  const [leaving, setLeaving] = useState(false);
  const [enterTick, setEnterTick] = useState(0);
  const [resizeTick, setResizeTick] = useState(0);
  const [done, setDone] = useState({ 1: false, 2: false, 3: false, 4: false }); // 4: 합성까지 끝남
  const [slots, setSlots] = useState({ 1: null, 2: null, 3: null });
  const [pick, setPick] = useState({ 1: { src: null, fromSample: false, confirm: false }, 2: { src: null, fromSample: false, confirm: false } });
  const [dragover, setDragover] = useState({ 1: false, 2: false });
  const [c3ui, setC3ui] = useState({ total: 0, neg: 0, pos: 0, canUndo: false });
  const [c4ui, setC4ui] = useState({ neg: 0, pos: 0, canUndo: false });
  const [editor, setEditor] = useState(null); // 다듬기 팝업: { kind: 'extract' | 'area', image, mask }
  const [settingsOpen, setSettingsOpen] = useState(false); // 합성 설정 팝업
  const [opts, setOpts] = useState({ refine: false, shape: false }); // Reference Mask Refine, Enable Shape Control
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(null); // 합성 진행 상황 (서버 작업 정보: status, progress, queue_position)
  const [result, setResult] = useState(null); // { entry: { canvas } 또는 { src }, fromHistory, id(결과 번호) }
  const [saved, setSaved] = useState(false);
  const [history, setHistory] = useState([]); // 합성한 결과 전체 (서버 목록 + 이번에 합성한 결과 isNew), 항목마다 saved
  const [activeHist, setActiveHist] = useState(null);
  const [panels, setPanels] = useState(() => ({ left: readPanel('left'), right: readPanel('right') }));

  /* ---------- 그리기용 데이터 (화면에 바로 보이지 않는 값은 ref에 둔다) ---------- */
  const data = useRef({ obj: null, bg: null, cutout: null, result: null });
  const s3 = useRef({ src: null, w: 0, h: 0, work: null, pts: [], hist: [], dw: 0, dh: 0 });
  const s4 = useRef({ src: null, w: 0, h: 0, work: null, pts: [], hist: [], dw: 0, dh: 0 });
  const stepRef = useRef(0);
  const navigate = useNavigate();
  const navigating = useRef(false);

  const c3Ref = useRef(null);
  const c4Ref = useRef(null);
  const cResRef = useRef(null);
  const historyRef = useRef(null);
  const pvImgRef = { 1: useRef(null), 2: useRef(null) };
  const slotRef = { 1: useRef(null), 2: useRef(null), 3: useRef(null) };
  const inputRef = { 1: useRef(null), 2: useRef(null) };

  /* ---------- 화면 전환 ---------- */
  // 나가는 화면이 살짝 위로 사라진 뒤, 다음 화면이 아래에서 부드럽게 떠오른다
  const go = (next) => new Promise((resolve) => {
    if (navigating.current) { resolve(); return; }
    if (stepRef.current !== next) {
      navigating.current = true;
      setLeaving(true);
      setTimeout(() => {
        setLeaving(false);
        stepRef.current = next;
        setStep(next);
        navigating.current = false;
        resolve();
      }, 200);
    } else {
      setEnterTick((t) => t + 1);
      resolve();
    }
  });

  const viewName = step === 0 ? 'intro' : String(step);
  const inSteps = typeof step === 'number' && step >= 1;
  const canPrev = inSteps && step > 1;
  const canNext = inSteps && step <= 3 && done[step];

  /* ---------- 1, 2단계: 사진 고르기 ---------- */
  const showPreview = (n, src, fromSample) => {
    setPick((p) => ({ ...p, [n]: { src, fromSample, confirm: true } }));
  };

  // 올린 파일(업로드 버튼 또는 끌어다 놓기)을 받아 큰 화면에 보여준다
  const takeFile = (n, f) => {
    if (!f) return;
    if (!/^image\//.test(f.type)) { showToast('이미지 파일만 업로드할 수 있습니다'); return; }
    showPreview(n, URL.createObjectURL(f), false);
  };

  const confirmPick = async (n) => {
    const src = pick[n].src;
    if (!src) return;
    setPick((p) => ({ ...p, [n]: { ...p[n], confirm: false } }));
    const img = await loadImage(src);
    const key = n === 1 ? 'obj' : 'bg';
    const changed = !data.current[key] || data.current[key].src !== src;
    // 서버에 사진을 올려 둔다 (명세 3-1). 화면은 기다리지 않고 넘어가고, 추출·합성 때 이 결과(사진 번호)를 쓴다
    const upload = changed || !data.current[key].upload
      ? uploadImage(src, n === 1 ? 'garment' : 'person')
      : data.current[key].upload;
    upload.catch((e) => showToast(`사진을 서버에 올리지 못했습니다: ${e.message}`));
    data.current[key] = { img, src, upload };
    if (changed) {
      if (n === 1) {
        data.current.cutout = null;
        s3.current.src = null;
        setDone((d) => ({ ...d, 3: false, 4: false }));
        setSlots((s) => ({ ...s, 3: null }));
      } else {
        s4.current.src = null;
        setDone((d) => ({ ...d, 4: false }));
      }
    }
    setDone((d) => ({ ...d, [n]: true }));
    await fly(pvImgRef[n].current, slotRef[n].current, () => setSlots((s) => ({ ...s, [n]: src })));
    go(n + 1);
  };

  // 단계에 들어올 때: 이미 고른 사진이 있으면 다시 보여 준다
  useLayoutEffect(() => {
    if (step !== 1 && step !== 2) return;
    const cur = step === 1 ? data.current.obj : data.current.bg;
    if (cur) showPreview(step, cur.src, SAMPLES[step].includes(cur.src));
  }, [step, enterTick]);

  // 사진을 칸 밖에 놓쳐도 브라우저가 그 사진을 열어 버리지 않게 막는다
  useEffect(() => {
    const stop = (e) => { if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files')) e.preventDefault(); };
    window.addEventListener('dragover', stop);
    window.addEventListener('drop', stop);
    return () => { window.removeEventListener('dragover', stop); window.removeEventListener('drop', stop); };
  }, []);

  /* ---------- 3단계: 점 찍기로 객체 추출 ---------- */
  const render3 = () => {
    const s = s3.current;
    const ctx = c3Ref.current.getContext('2d');
    ctx.clearRect(0, 0, s.dw, s.dh);
    ctx.drawImage(s.work, 0, 0, s.dw, s.dh);
    s.pts.forEach((p) => drawDot(ctx, p.x * s.dw, p.y * s.dh, p.neg ? '#e11d48' : '#16171b'));
    const pos = s.pts.filter((p) => !p.neg).length;
    const next = { total: s.pts.length, neg: s.pts.length - pos, pos, canUndo: s.hist.length > 0 };
    setC3ui((prev) => (sameUi(prev, next) ? prev : next));
  };

  const enterStep3 = () => {
    const obj = data.current.obj;
    if (!obj) return;
    const s = s3.current;
    if (s.src !== obj.src) {
      const w = makeWork(obj.img);
      Object.assign(s, { src: obj.src, work: w.work, w: w.w, h: w.h, pts: [], hist: [], edited: null, editedKey: null });
    }
    const d = boxFit(c3Ref.current, s.w, s.h);
    s.dw = d.w; s.dh = d.h;
    c3Ref.current.width = d.w; c3Ref.current.height = d.h;
    render3();
  };

  // 실행 취소: 바꾸기 직전의 점 목록을 쌓아 두고 하나씩 꺼내 복원한다 (최대 50단계)
  const pushHist3 = () => {
    const s = s3.current;
    s.hist.push(s.pts.map((q) => ({ x: q.x, y: q.y, neg: q.neg })));
    if (s.hist.length > 50) s.hist.shift();
  };

  const onDown3 = (e) => {
    const s = s3.current;
    if (!s.work) return;
    const p = pointer(e, c3Ref.current);
    const hit = s.pts.findIndex((q) => Math.hypot(q.x * s.dw - p.px, q.y * s.dh - p.py) < 11);
    pushHist3();
    if (hit >= 0) s.pts.splice(hit, 1);
    else s.pts.push({ x: p.x, y: p.y, neg: e.button === 2 });
    render3();
  };

  const reset3 = () => {
    const s = s3.current;
    if (!s.work || !s.pts.length) return;
    pushHist3();
    s.pts = [];
    render3();
  };

  const undo3 = () => {
    const s = s3.current;
    if (!s.work || !s.hist.length) return;
    s.pts = s.hist.pop();
    render3();
  };

  // 확인: 찍은 점을 서버에 보내 SAM2로 상의를 찾고(명세 4-1), 그 결과로 다듬기 팝업을 연다.
  // 점을 바꾸지 않았으면 서버에 다시 묻지 않고, 지난번에 다듬은 영역(없으면 지난 SAM2 결과)에서 이어서 한다.
  const confirm3 = async () => {
    const s = s3.current;
    if (!s.work || !s.pts.some((p) => !p.neg) || s.extracting) return;
    const key = JSON.stringify(s.pts);
    if (s.edited && s.editedKey === key) { setEditor({ kind: 'extract', image: s.work, mask: s.edited }); return; }
    if (s.samMask && s.samKey === key) { setEditor({ kind: 'extract', image: s.work, mask: s.samMask }); return; }

    s.extracting = true;
    showToast('상의를 찾는 중입니다…');
    try {
      const { image_id: imageId } = await data.current.obj.upload;
      const points = s.pts.map((p) => ({ x: p.x, y: p.y, label: p.neg ? 0 : 1 }));
      const ext = await extractGarment(imageId, points);
      const mask = await maskFromUrl(ext.mask_url, s.w, s.h);
      Object.assign(s, { samMask: mask, samKey: key });
      data.current.extraction = ext; // 4단계 합성에서 extraction_id를 쓴다
      setEditor({ kind: 'extract', image: s.work, mask });
    } catch (e) {
      showToast(`상의를 찾지 못했습니다: ${e.message}`);
    } finally {
      s.extracting = false;
    }
  };

  // 다듬기 완료: 다듬은 영역으로 상의를 오려 내고 4단계로 간다
  const finish3 = async (mask) => {
    const s = s3.current;
    const bb = maskBBox(mask);
    if (!bb) return;
    s.edited = newCanvas(s.w, s.h);
    s.edited.getContext('2d').drawImage(mask, 0, 0);
    s.editedKey = JSON.stringify(s.pts);
    setEditor(null);
    const cut = newCanvas(s.w, s.h);
    const cx = cut.getContext('2d');
    cx.drawImage(s.work, 0, 0);
    cx.globalCompositeOperation = 'destination-in';
    cx.drawImage(s.edited, 0, 0);
    const cutout = { canvas: cut, bbox: bb };
    data.current.cutout = cutout;
    setDone((d) => ({ ...d, 3: true, 4: false }));
    await fly(c3Ref.current, slotRef[3].current, () => setSlots((sl) => ({ ...sl, 3: cutout })));
    go(4);
  };

  /* ---------- 4단계: 합성 영역 지정 (3단계와 같이 점 → SAM2 → 팝업에서 브러시와 지우개) ---------- */
  const render4 = () => {
    const s = s4.current;
    const ctx = c4Ref.current.getContext('2d');
    ctx.clearRect(0, 0, s.dw, s.dh);
    ctx.drawImage(s.work, 0, 0, s.dw, s.dh);
    s.pts.forEach((p) => drawDot(ctx, p.x * s.dw, p.y * s.dh, p.neg ? '#e11d48' : '#16171b'));
    const pos = s.pts.filter((p) => !p.neg).length;
    const next = { neg: s.pts.length - pos, pos, canUndo: s.hist.length > 0 };
    setC4ui((prev) => (sameUi(prev, next) ? prev : next));
  };

  const enterStep4 = () => {
    const bg = data.current.bg;
    if (!bg) return;
    const s = s4.current;
    if (s.src !== bg.src) {
      const w = makeWork(bg.img);
      Object.assign(s, { src: bg.src, work: w.work, w: w.w, h: w.h, pts: [], hist: [], samMask: null, samKey: null, edited: null, editedKey: null });
    }
    const d = boxFit(c4Ref.current, s.w, s.h);
    s.dw = d.w; s.dh = d.h;
    c4Ref.current.width = d.w; c4Ref.current.height = d.h;
    render4();
  };

  // 실행 취소: 바꾸기 직전의 점 목록을 쌓아 두고 하나씩 꺼내 복원한다 (최대 50단계)
  const pushHist4 = () => {
    const s = s4.current;
    s.hist.push(s.pts.map((q) => ({ x: q.x, y: q.y, neg: q.neg })));
    if (s.hist.length > 50) s.hist.shift();
  };

  const onDown4 = (e) => {
    const s = s4.current;
    if (!s.work) return;
    const p = pointer(e, c4Ref.current);
    const hit = s.pts.findIndex((q) => Math.hypot(q.x * s.dw - p.px, q.y * s.dh - p.py) < 11);
    pushHist4();
    if (hit >= 0) s.pts.splice(hit, 1);
    else s.pts.push({ x: p.x, y: p.y, neg: e.button === 2 });
    render4();
  };

  const reset4 = () => {
    const s = s4.current;
    if (!s.work || !s.pts.length) return;
    pushHist4();
    s.pts = [];
    render4();
  };

  const undo4 = () => {
    const s = s4.current;
    if (!s.work || !s.hist.length) return;
    s.pts = s.hist.pop();
    render4();
  };

  // 확인: 인물 사진에 찍은 점을 서버에 보내 SAM2로 지금 입은 상의 영역을 찾고(3단계와 같은 명세 4-1), 그 결과로 다듬기 팝업을 연다.
  // 이 추출 결과는 합성 영역 그림으로만 쓰고, 합성 요청의 extraction_id는 3단계 것을 그대로 쓴다.
  // 점을 바꾸지 않았으면 서버에 다시 묻지 않고, 지난번에 다듬은 영역(없으면 지난 SAM2 결과)에서 이어서 한다.
  const confirm4 = async () => {
    const s = s4.current;
    if (!s.work || !s.pts.some((p) => !p.neg) || s.extracting || !data.current.cutout) return;
    const key = JSON.stringify(s.pts);
    if (s.edited && s.editedKey === key) { setEditor({ kind: 'area', image: s.work, mask: s.edited }); return; }
    if (s.samMask && s.samKey === key) { setEditor({ kind: 'area', image: s.work, mask: s.samMask }); return; }

    s.extracting = true;
    showToast('합성 영역을 찾는 중입니다…');
    try {
      const { image_id: imageId } = await data.current.bg.upload;
      const points = s.pts.map((p) => ({ x: p.x, y: p.y, label: p.neg ? 0 : 1 }));
      const ext = await extractGarment(imageId, points);
      const mask = await maskFromUrl(ext.mask_url, s.w, s.h);
      Object.assign(s, { samMask: mask, samKey: key });
      setEditor({ kind: 'area', image: s.work, mask });
    } catch (e) {
      showToast(`합성 영역을 찾지 못했습니다: ${e.message}`);
    } finally {
      s.extracting = false;
    }
  };

  // 다듬기 완료: 다듬은 영역을 기억하고 합성 설정 팝업을 연다
  const finish4 = (mask) => {
    const s = s4.current;
    s.edited = newCanvas(s.w, s.h);
    s.edited.getContext('2d').drawImage(mask, 0, 0);
    s.editedKey = JSON.stringify(s.pts);
    setDone((d) => ({ ...d, 4: false }));
    setEditor(null);
    setSettingsOpen(true);
  };

  const showResult = async (entry, fromHistory, id) => {
    setResult({ entry, fromHistory, id });
    await go('result');
  };

  // 다듬기 팝업 닫기 (점 다시 찍기). 다듬던 내용은 버린다.
  const closeEditor = useCallback(() => setEditor(null), []);

  // 합성 설정 팝업의 "이전": 입힐 곳 다듬기로 돌아간다 (다듬은 영역에서 이어서)
  const backToArea = () => {
    setSettingsOpen(false);
    const s = s4.current;
    if (s.edited) setEditor({ kind: 'area', image: s.work, mask: s.edited });
  };

  // 합성 설정 팝업의 "합성 시작": 서버에 합성을 요청하고(명세 5-1), 2초마다 진행을 확인한 뒤(5-2) 결과를 받는다(5-3).
  // 고른 설정(opts)은 아직 서버가 쓰지 않아 보내지 않는다.
  const startCompose = async () => {
    if (!s4.current.edited || !data.current.cutout) return;
    const ext = data.current.extraction;
    if (!ext) { showToast('3단계에서 상의를 다시 지정해 주십시오'); return; }
    setSettingsOpen(false);
    setProgress(null);
    setBusy(true);
    try {
      const { image_id: personId } = await data.current.bg.upload;
      const area = await areaMaskBlob(s4.current.edited);
      const job = await requestCompose(ext.extraction_id, personId, area);
      const resultId = await waitForJob(job.job_id, setProgress);
      data.current.resultId = resultId; // "저장" 때 서버에 알릴 결과 번호
      const res = await getResult(resultId);
      const img = await loadImage(res.image_url);
      const out = newCanvas(img.naturalWidth, img.naturalHeight);
      out.getContext('2d').drawImage(img, 0, 0);
      data.current.result = out;
      setSaved(false);
      // 합성이 끝나면 저장하지 않아도 내 작업 기록 맨 위에 붙인다
      setHistory((h) => [
        { id: resultId, d: formatKoreanDate(res.created_at), entry: { canvas: out }, isNew: true, saved: false },
        ...h.filter((x) => x.id !== resultId),
      ]);
      setActiveHist(resultId);
      await showResult({ canvas: out }, false, resultId);
    } catch (e) {
      showToast(`합성하지 못했습니다: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  /* ---------- 결과, 저장, 작업 기록 ---------- */
  // 화면에 들어오면 합성한 결과 전체(저장 여부 무관)를 최신순으로 받아 온다. 받기 전에 이번에 합성한 결과(isNew)는 그대로 둔다
  useEffect(() => {
    let ignore = false;
    listResults({ sort: 'new' })
      .then((res) => {
        if (ignore) return;
        const fromServer = res.items.map((r) => ({
          id: r.result_id, d: formatKoreanDate(r.created_at), entry: { src: r.image_url, thumb: r.thumb_url }, isNew: false, saved: r.saved,
        }));
        setHistory((h) => {
          const fresh = h.filter((x) => x.isNew);
          return [...fresh, ...fromServer.filter((x) => !fresh.some((f) => f.id === x.id))];
        });
      })
      .catch((e) => { if (!ignore) showToast(e.message); });
    return () => { ignore = true; };
  }, [showToast]);

  // 저장: 서버에 "저장함"으로 알린다(명세 6-2). 저장한 결과만 마이페이지 사진첩에 나온다.
  // 방금 합성한 결과, 내 작업 기록에서 연 저장 안 한 결과 모두 저장할 수 있다
  const save = async () => {
    if (!result || !result.id || saved) return;
    const { id } = result;
    setSaved(true);
    try {
      await updateResult(id, { saved: true });
    } catch (e) {
      setSaved(false);
      showToast(`저장하지 못했습니다: ${e.message}`);
      return;
    }
    setHistory((h) => h.map((x) => (x.id === id ? { ...x, saved: true } : x)));
    showToast('사진첩에 저장했습니다');
  };

  const redo = () => { go(result && result.fromHistory ? 1 : 4); };

  const openHistory = (item) => {
    setActiveHist(item.id);
    setSaved(!!item.saved);
    showResult(item.entry, true, item.id);
  };

  // 3, 4단계에 들어오거나 창 크기가 바뀌면 캔버스를 칸에 다시 맞춘다
  useLayoutEffect(() => {
    if (step === 3) enterStep3();
    else if (step === 4) enterStep4();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, enterTick, resizeTick]);

  // 결과 화면 그리기
  useLayoutEffect(() => {
    if (step !== 'result' || !result) return undefined;
    let cancelled = false;
    (async () => {
      const { entry } = result;
      let src; let w; let h;
      if (entry.canvas) { src = entry.canvas; w = src.width; h = src.height; } else { src = await loadImage(entry.src); w = src.naturalWidth; h = src.naturalHeight; }
      if (cancelled || !cResRef.current) return;
      const d = boxFit(cResRef.current, w, h);
      cResRef.current.width = d.w; cResRef.current.height = d.h;
      cResRef.current.getContext('2d').drawImage(src, 0, 0, d.w, d.h);
    })();
    return () => { cancelled = true; };
  }, [step, result, resizeTick]);

  // 스크롤바가 보이는 만큼 목록을 오른쪽으로 넓혀서, 사진 폭이 왼쪽 진행 상황의 사진과 같아지게 한다
  useLayoutEffect(() => {
    const el = historyRef.current;
    if (!el) return;
    el.style.marginRight = '0px';
    const sb = el.offsetWidth - el.clientWidth;
    el.style.marginRight = (-sb) + 'px';
  }, [history, resizeTick, panels]);

  useEffect(() => {
    let t = null;
    const onResize = () => { clearTimeout(t); t = setTimeout(() => setResizeTick((x) => x + 1), 150); };
    window.addEventListener('resize', onResize);
    return () => { clearTimeout(t); window.removeEventListener('resize', onResize); };
  }, []);

  /* ---------- 양쪽 패널 접기 / 펼치기 (상태는 이 브라우저에 기억) ---------- */
  const togglePanel = (side) => {
    setPanels((p) => {
      const next = p[side] === 'open' ? 'closed' : 'open';
      writePanel(side, next);
      return { ...p, [side]: next };
    });
    // 폭이 바뀌는 애니메이션이 끝난 뒤 가운데 캔버스를 칸에 다시 맞춘다
    setTimeout(() => setResizeTick((x) => x + 1), 300);
  };

  const panelToggle = (side, label) => {
    const text = label + (panels[side] === 'open' ? ' 접기' : ' 열기');
    return (
      <button type="button" className="sg-toggle" aria-expanded={panels[side] === 'open'} aria-label={text} title={text} onClick={() => togglePanel(side)}>
        <ArrowIcon />
      </button>
    );
  };

  const viewClass = (name) => 'sg-view' + (leaving && viewName === name ? ' leaving' : '');

  const renderPick = (n) => {
    const p = pick[n];
    return (
      <section className={viewClass(String(n))} data-view={String(n)} hidden={viewName !== String(n)}>
        <div className="sg-head">
          <h2 className="sg-title">{PICK_TEXT[n].title}</h2>
          <div className="sg-head-tools">
            <span className="sg-sample-label">예시</span>
            <div className="sg-samples">
              {SAMPLES[n].map((src) => (
                <button key={src} type="button" className={'sg-sample' + (p.fromSample && p.src === src ? ' selected' : '')} onClick={() => showPreview(n, src, true)}>
                  <img src={src} alt="" />
                </button>
              ))}
            </div>
            <label className="sg-upload-btn">
              <input ref={inputRef[n]} type="file" accept="image/*" hidden onChange={(e) => { takeFile(n, e.target.files[0]); e.target.value = ''; }} />
              <UploadIcon />
              업로드
            </label>
          </div>
        </div>
        <div
          className={'sg-zone' + (p.src ? ' has-img' : '') + (dragover[n] ? ' dragover' : '')}
          onClick={(e) => { if (!p.src && !e.target.closest('button')) inputRef[n].current.click(); }}
          onDragEnter={(e) => { e.preventDefault(); setDragover((d) => ({ ...d, [n]: true })); }}
          onDragOver={(e) => { e.preventDefault(); setDragover((d) => ({ ...d, [n]: true })); }}
          onDragLeave={(e) => { e.preventDefault(); setDragover((d) => ({ ...d, [n]: false })); }}
          onDrop={(e) => {
            e.preventDefault();
            setDragover((d) => ({ ...d, [n]: false }));
            takeFile(n, e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]);
          }}
        >
          <div className="sg-zone-empty">
            <b>사진을 이곳에 끌어다 놓으십시오</b>
            <span>오른쪽 위 업로드 버튼으로도 선택할 수 있습니다</span>
            <div className="sg-zone-help">
              <strong>{PICK_TEXT[n].helpTitle}</strong>
              <p>{PICK_TEXT[n].help}</p>
            </div>
          </div>
          <div className="sg-zone-stage">{p.src && <img ref={pvImgRef[n]} src={p.src} alt="" />}</div>
          <button type="button" className="sg-confirm sg-zone-confirm" hidden={!p.confirm} onClick={() => confirmPick(n)}>이 사진 사용</button>
        </div>
      </section>
    );
  };

  const shellState = step === 0 ? 'intro' : step === 'result' ? 'result' : 'step';
  const fromHistory = !!(result && result.fromHistory);

  return (
    <>
      <TopNav />

      <div className="sg-shell" data-state={shellState} data-left={panels.left} data-right={panels.right}>
        {/* 왼쪽: 고른 결과가 작아져서 쌓이는 곳 */}
        <aside className="sg-left">
          <div className="sg-side-head">
            <h2 className="sg-side-title">진행 상황</h2>
            {panelToggle('left', '진행 상황')}
            <span className="sg-rail-label">진행 상황</span>
          </div>

          {SLOTS.map((sl) => (
            <button
              key={sl.n}
              type="button"
              className={'sg-slot' + (step === sl.n ? ' current' : '') + (done[sl.n] ? ' done' : '')}
              onClick={() => { if (done[sl.n]) go(sl.n); }}
            >
              <span className="sg-slot-body">
                <span className="sg-slot-name">{sl.name}</span>
                <span className={'sg-slot-thumb' + (sl.n === 3 ? ' sg-checker' : '')} ref={slotRef[sl.n]}>
                  {!slots[sl.n] && <em>{sl.empty}</em>}
                  {slots[sl.n] && sl.n !== 3 && <img src={slots[sl.n]} alt="" />}
                  {slots[sl.n] && sl.n === 3 && <DrawnCanvas width={480} height={300} source={slots[3]} draw={drawCutoutThumb} />}
                </span>
              </span>
            </button>
          ))}
        </aside>

        {/* 가운데: 단계별 안내 */}
        <main className="sg-main">
          <div className="sg-bar">
            <button type="button" className="sg-nav-btn" disabled={!canPrev} onClick={() => { if (canPrev) go(step - 1); }}>← 이전</button>
            <ol className="sg-stepper">
              {STEPS.map((s) => (
                <li key={s.n} className={(s.n === step ? 'current' : '') + (done[s.n] && s.n !== step ? ' done' : '')}>
                  <span>{s.n}</span>{s.label}
                </li>
              ))}
            </ol>
            <button type="button" className="sg-nav-btn" disabled={!canNext} onClick={() => { if (canNext) go(step + 1); }}>다음 →</button>
          </div>

          <div className="sg-stage">
            {/* 시작 */}
            <section className={viewClass('intro')} data-view="intro" hidden={viewName !== 'intro'}>
              <p className="sg-eyebrow">MOA</p>
              <h1 className="sg-hero-title">원하는 상의를 입은 모습을<br />사진으로 미리 확인합니다</h1>
              <p className="sg-hero-desc">상의 사진 한 장과 인물 사진 한 장이 필요합니다.</p>
              <ul className="sg-intro-steps">
                <li><b>1</b> 상의 사진 선택</li>
                <li><b>2</b> 인물 사진 선택</li>
                <li><b>3</b> 상의 영역 지정</li>
                <li><b>4</b> 합성 영역 지정</li>
              </ul>
              <button type="button" className="sg-big-btn" onClick={() => go(1)}>시작</button>
            </section>

            {renderPick(1)}
            {renderPick(2)}

            {/* 3단계 */}
            <section className={viewClass('3')} data-view="3" hidden={viewName !== '3'}>
              <h2 className="sg-title">3. 상의 영역 지정</h2>
              <div className="sg-help">
                <b>사용 방법</b>
                <p><em>상의</em>를 왼쪽 클릭하여 선택합니다.<br />제외할 부분은 오른쪽 클릭합니다.</p>
              </div>
              <div className="sg-canvas-box">
                <canvas ref={c3Ref} className="sg-canvas" hidden={!done[1]} onMouseDown={onDown3} onContextMenu={(e) => e.preventDefault()} />
                <p className="sg-canvas-empty" hidden={done[1]}>1단계에서 상의 사진을 먼저 선택해야 합니다.</p>
              </div>
              <div className="sg-actions">
                <span className="sg-chip">포함 {c3ui.pos}개 · 제외 {c3ui.neg}개</span>
                <button type="button" className="sg-ghost" disabled={!done[1] || !c3ui.canUndo} onClick={undo3}>실행 취소</button>
                <button type="button" className="sg-ghost" onClick={reset3}>전체 삭제</button>
                <button type="button" className="sg-confirm" disabled={!done[1] || c3ui.pos === 0} onClick={confirm3}>확인</button>
              </div>
            </section>

            {/* 4단계 */}
            <section className={viewClass('4')} data-view="4" hidden={viewName !== '4'}>
              <h2 className="sg-title">4. 합성 영역 지정</h2>
              <div className="sg-help">
                <b>사용 방법</b>
                <p>인물이 입고 있는 <em>상의</em>를 왼쪽 클릭하여 선택합니다.<br />제외할 부분은 오른쪽 클릭합니다.</p>
              </div>
              <div className="sg-canvas-box">
                <canvas ref={c4Ref} className="sg-canvas" hidden={!done[2]} onMouseDown={onDown4} onContextMenu={(e) => e.preventDefault()} />
                <p className="sg-canvas-empty" hidden={done[2]}>2단계에서 인물 사진을 먼저 선택해야 합니다.</p>
              </div>
              <div className="sg-actions">
                <span className="sg-chip">포함 {c4ui.pos}개 · 제외 {c4ui.neg}개</span>
                <button type="button" className="sg-ghost" disabled={!done[2] || !c4ui.canUndo} onClick={undo4}>실행 취소</button>
                <button type="button" className="sg-ghost" onClick={reset4}>전체 삭제</button>
                <button type="button" className="sg-confirm" disabled={!done[2] || c4ui.pos === 0} onClick={confirm4}>확인</button>
              </div>
            </section>

            {/* 결과 */}
            <section className={viewClass('result')} data-view="result" hidden={viewName !== 'result'}>
              <h2 className="sg-title">{fromHistory && saved ? '저장된 결과' : '합성 결과'}</h2>
              <div className="sg-canvas-box sg-result-box">
                <canvas ref={cResRef} className="sg-canvas" />
              </div>
              <div className="sg-actions sg-actions-center">
                <button type="button" className="sg-confirm" disabled={saved} onClick={save}>{saved ? '저장됨' : '저장'}</button>
                <button type="button" className="sg-ghost" onClick={redo}>{fromHistory ? '새로 합성' : '다시 합성'}</button>
              </div>
            </section>
          </div>
        </main>

        {/* 오른쪽: 합성한 결과 전체 (저장 여부 무관) */}
        <aside className="sg-right">
          <div className="sg-side-head">
            <h2 className="sg-side-title">내 작업 기록</h2>
            {panelToggle('right', '내 작업 기록')}
            <span className="sg-rail-label">내 작업 기록</span>
          </div>
          <div className="sg-history" ref={historyRef}>
            {history.map((item) => (
              <button
                key={item.id}
                type="button"
                className={'sg-hist-item' + (item.isNew ? ' sg-hist-fresh' : '') + (activeHist === item.id ? ' active' : '')}
                onClick={() => openHistory(item)}
              >
                {/* 왼쪽 진행 상황처럼 위에 이름(여기서는 생성 날짜), 아래에 사진 */}
                <span className="sg-hist-date">{item.d}</span>
                <div className="sg-hist-thumb">
                  {item.entry.canvas
                    ? <DrawnCanvas width={400} height={300} source={item.entry.canvas} draw={drawHistThumb} />
                    : <img src={item.entry.thumb || item.entry.src} alt="" />}
                  {item.isNew && <span className="sg-hist-new">NEW</span>}
                </div>
              </button>
            ))}
          </div>
        </aside>
      </div>

      {/* 합성 중: 끝날 때까지 모든 클릭을 막는다 */}
      <div className={'sg-busy' + (busy ? ' show' : '')}>
        <div className="sg-busy-box">
          <div className="sg-spinner" />
          <p>합성 중입니다</p>
          <span>
            완료될 때까지 잠시 기다려 주십시오
            {progress && progress.status === 'queued' && progress.queue_position > 0 && ` (대기 ${progress.queue_position}번째)`}
            {progress && progress.status === 'running' && progress.progress > 0 && ` (${Math.round(progress.progress * 100)}%)`}
          </span>
        </div>
      </div>

      {/* 3, 4단계 다듬기 팝업 */}
      {editor && editor.kind === 'extract' && (
        <MaskEditor
          key={editor.kind}
          title="상의 영역 수정"
          help="빠진 부분은 브러시로 칠하고, 잘못 잡힌 부분은 지우개로 지웁니다."
          image={editor.image}
          mask={editor.mask}
          tint="rgba(125, 26, 36, 0.5)"
          cancelLabel="점 재지정"
          doneLabel="다음 단계"
          onCancel={closeEditor}
          onDone={finish3}
        />
      )}
      {editor && editor.kind === 'area' && (
        <MaskEditor
          key={editor.kind}
          title="합성 영역 수정"
          help="빠진 부분은 브러시로 칠하고, 잘못 잡힌 부분은 지우개로 지웁니다."
          image={editor.image}
          mask={editor.mask}
          tint="rgba(31, 81, 56, 0.55)"
          cancelLabel="점 재지정"
          doneLabel="다음"
          onCancel={closeEditor}
          onDone={finish4}
        />
      )}

      {/* 합성 설정 팝업 */}
      {settingsOpen && (
        <div className="sg-modal" role="dialog" aria-modal="true" aria-label="합성 설정">
          <div className="sg-modal-box sg-modal-narrow">
            <div className="sg-modal-head">
              <h3>합성 설정</h3>
              <button type="button" className="sg-modal-close" aria-label="닫기" onClick={() => setSettingsOpen(false)}>×</button>
            </div>
            <label className="sg-check">
              <input type="checkbox" checked={opts.refine} onChange={(e) => setOpts((o) => ({ ...o, refine: e.target.checked }))} />
              <span>
                <b>상의 경계 보정<small>Reference Mask Refine</small></b>
                <span>지정한 상의 영역의 경계를 한 번 더 정리합니다.</span>
              </span>
            </label>
            <label className="sg-check">
              <input type="checkbox" checked={opts.shape} onChange={(e) => setOpts((o) => ({ ...o, shape: e.target.checked }))} />
              <span>
                <b>영역 모양 반영<small>Enable Shape Control</small></b>
                <span>지정한 합성 영역의 모양에 맞춰 상의를 입힙니다. 선택하지 않으면 영역을 둘러싼 사각형 범위 안에서 형태를 자동으로 맞춥니다.</span>
              </span>
            </label>
            <div className="sg-actions">
              <button type="button" className="sg-ghost" onClick={backToArea}>이전</button>
              <button type="button" className="sg-confirm" onClick={startCompose}>합성 시작</button>
            </div>
          </div>
        </div>
      )}

      <div className={'sg-toast' + (toast.show ? ' show' : '')}>{toast.msg}</div>
    </>
  );
}
