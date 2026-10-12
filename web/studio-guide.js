/* 합성하기: 단계별 안내 화면 (디자인 시안)
   실제 SAM 추출이나 AI 합성은 하지 않는다. 점 찍기, 브러시, 합성중 화면, 결과 화면의 흐름과 모양만 보여주는 시안이다.
   캔버스는 그리기만 하고 픽셀을 읽어 오지 않으므로, 파일(file://)로 열어도 동작한다. */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const shell = $('#sg-shell');
  const views = $$('.sg-view');
  const btnPrev = $('#btn-prev');
  const btnNext = $('#btn-next');

  const SAMPLES = {
    1: ['assets/gallery/AutumnWarm_Male.jpg', 'assets/gallery/SpringWarm_Female.jpg', 'assets/gallery/SummerCool_Female.jpg'],
    2: ['assets/samples/sample-object-person.jpg', 'assets/gallery/girl_Santorini.jpg', 'assets/gallery/Paris_Female.jpg'],
  };

  const HISTORY = [
    { src: 'assets/gallery/MtFuji_Female.jpg', d: '2026.10.08 20:45' },
    { src: 'assets/gallery/NewYork_Male.jpg',       d: '2026.10.07 15:12' },
    { src: 'assets/gallery/Paris_Female.jpg',       d: '2026.10.06 09:30' },
    { src: 'assets/gallery/girl_sitting.jpg',      d: '2026.10.04 18:20' },
    { src: 'assets/gallery/BaseballCap_Male.jpg',   d: '2026.10.02 12:05' },
  ];

  const state = {
    step: 0,               // 0 시작, 1~4 단계, 'result' 결과
    obj: null,             // { img, src } 1단계에서 고른 객체 이미지
    bg: null,              // { img, src } 2단계에서 고른 배경 이미지
    cutout: null,          // { canvas, bbox } 3단계에서 추출한 객체
    result: null,          // 합성 결과 캔버스
    saved: false,
    done: { 1: false, 2: false, 3: false },
  };
  const pending = { 1: null, 2: null };

  /* ---------- 공통 도우미 ---------- */
  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = src;
    });
  }

  function makeWork(img) {
    const sc = Math.min(1, 1000 / Math.max(img.naturalWidth, img.naturalHeight));
    const w = Math.round(img.naturalWidth * sc);
    const h = Math.round(img.naturalHeight * sc);
    const c = document.createElement('canvas');
    c.width = w;
    c.height = h;
    c.getContext('2d').drawImage(img, 0, 0, w, h);
    return { work: c, w, h };
  }

  function fit(w, h, maxW, maxH) {
    const sc = Math.min(maxW / w, maxH / h, 1);
    return { w: Math.round(w * sc), h: Math.round(h * sc) };
  }

  // 캔버스를 둘러싼 칸의 남는 공간에 맞춰 크기를 정한다 (한 화면 고정이라 페이지가 늘어나지 않는다)
  function boxFit(canvas, w, h) {
    const box = canvas.parentElement;
    const cs = getComputedStyle(box);
    const aw = box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const ah = box.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    return fit(w, h, Math.max(160, aw), Math.max(160, ah));
  }

  function drawCover(ctx, src, sx, sy, sw, sh, dw, dh) {
    // 원본 영역(sx, sy, sw, sh)을 비율을 유지하며 dw x dh 가득 채워 그린다
    const sc = Math.max(dw / sw, dh / sh);
    const w = sw * sc;
    const h = sh * sc;
    ctx.drawImage(src, sx, sy, sw, sh, (dw - w) / 2, (dh - h) / 2, w, h);
  }

  function drawContain(ctx, src, sx, sy, sw, sh, dw, dh) {
    const sc = Math.min(dw / sw, dh / sh);
    const w = sw * sc;
    const h = sh * sc;
    ctx.drawImage(src, sx, sy, sw, sh, (dw - w) / 2, (dh - h) / 2, w, h);
  }

  let toastTimer = null;
  function toast(msg) {
    const el = $('#sg-toast');
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 2000);
  }

  // 선택한 사진이 작아지면서 왼쪽 칸으로 이동하는 효과
  function fly(fromEl, toEl, finish) {
    return new Promise((resolve) => {
      const r1 = fromEl.getBoundingClientRect();
      const r2 = toEl.getBoundingClientRect();
      // 왼쪽 패널이 접혀 있어 목적지 칸이 보이지 않으면 날아가는 효과만 건너뛰고 결과는 그대로 반영한다
      if (!r2.width || !r2.height) { finish(); resolve(); return; }
      let clone;
      if (fromEl instanceof HTMLCanvasElement) {
        clone = document.createElement('canvas');
        clone.width = fromEl.width;
        clone.height = fromEl.height;
        clone.getContext('2d').drawImage(fromEl, 0, 0);
      } else {
        clone = new Image();
        clone.src = fromEl.src;
      }
      clone.className = 'sg-fly';
      Object.assign(clone.style, { left: r1.left + 'px', top: r1.top + 'px', width: r1.width + 'px', height: r1.height + 'px' });
      document.body.appendChild(clone);
      fromEl.style.visibility = 'hidden';
      clone.getBoundingClientRect();
      requestAnimationFrame(() => {
        clone.classList.add('landing');
        Object.assign(clone.style, { left: r2.left + 'px', top: r2.top + 'px', width: r2.width + 'px', height: r2.height + 'px' });
      });
      setTimeout(() => {
        fromEl.style.visibility = '';
        finish();
        toEl.classList.add('pop');
        setTimeout(() => toEl.classList.remove('pop'), 650);
        clone.remove();
        resolve();
      }, 900);
    });
  }

  /* ---------- 화면 전환 ---------- */
  function applyStep(step) {
    state.step = step;
    const viewName = step === 0 ? 'intro' : String(step);
    views.forEach((v) => { v.hidden = v.dataset.view !== viewName; });
    shell.dataset.state = step === 0 ? 'intro' : step === 'result' ? 'result' : 'step';

    $$('#sg-stepper li').forEach((li) => {
      const n = Number(li.dataset.step);
      li.classList.toggle('current', n === step);
      li.classList.toggle('done', n < 4 && state.done[n] && n !== step);
    });
    $$('.sg-slot').forEach((s) => {
      const n = Number(s.dataset.slot);
      s.classList.toggle('current', n === step);
      s.classList.toggle('done', !!state.done[n]);
    });

    const inSteps = typeof step === 'number' && step >= 1;
    btnPrev.disabled = !(inSteps && step > 1);
    btnNext.disabled = !(inSteps && step <= 3 && state.done[step]);

    if (step === 1) enterPick(1);
    if (step === 2) enterPick(2);
    if (step === 3) enterStep3();
    if (step === 4) enterStep4();
  }

  // 화면 전환: 나가는 화면이 살짝 위로 사라진 뒤, 다음 화면이 아래에서 부드럽게 떠오른다
  let navigating = false;
  function go(step) {
    return new Promise((resolve) => {
      if (navigating) { resolve(); return; }
      const viewName = step === 0 ? 'intro' : String(step);
      const cur = views.find((v) => !v.hidden);
      if (cur && cur.dataset.view !== viewName) {
        navigating = true;
        cur.classList.add('leaving');
        setTimeout(() => {
          cur.classList.remove('leaving');
          applyStep(step);
          navigating = false;
          resolve();
        }, 200);
      } else {
        applyStep(step);
        resolve();
      }
    });
  }

  btnPrev.addEventListener('click', () => { if (typeof state.step === 'number' && state.step > 1) go(state.step - 1); });
  btnNext.addEventListener('click', () => { if (typeof state.step === 'number' && state.step <= 3 && state.done[state.step]) go(state.step + 1); });
  $('#btn-start').addEventListener('click', () => go(1));
  $$('.sg-slot').forEach((s) => {
    s.addEventListener('click', () => {
      const n = Number(s.dataset.slot);
      if (state.done[n]) go(n);
    });
  });

  /* ---------- 1, 2단계: 사진 고르기 ---------- */
  function setSlotImg(n, src) {
    const slot = $('#slot-' + n);
    slot.innerHTML = '<img src="' + src + '" alt="">';
  }

  function showPreview(n, src, btn) {
    pending[n] = src;
    $('#pv-' + n).innerHTML = '<img src="' + src + '" alt="">';
    $('#zone-' + n).classList.add('has-img');
    $$('#samples-' + n + ' .sg-sample').forEach((x) => x.classList.toggle('selected', x === btn));
    const c = $('#confirm-' + n);
    c.hidden = false;
    c.disabled = false;
  }

  // 올린 파일(업로드 버튼 또는 끌어다 놓기)을 받아 큰 화면에 보여준다
  function takeFile(n, f) {
    if (!f) return;
    if (!/^image\//.test(f.type)) { toast('이미지 파일만 업로드할 수 있습니다'); return; }
    showPreview(n, URL.createObjectURL(f), null);
  }

  function initPick(n) {
    const box = $('#samples-' + n);
    SAMPLES[n].forEach((src) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'sg-sample';
      b.dataset.src = src;
      b.innerHTML = '<img src="' + src + '" alt="">';
      b.addEventListener('click', () => showPreview(n, src, b));
      box.appendChild(b);
    });
    const input = $('[data-upload="' + n + '"]');
    input.addEventListener('change', (e) => {
      takeFile(n, e.target.files[0]);
      e.target.value = '';
    });

    // 큰 화면 전체가 올리는 자리: 끌어다 놓거나, 비어 있을 때는 눌러서 파일을 고른다
    const zone = $('#zone-' + n);
    zone.addEventListener('click', (e) => {
      if (!zone.classList.contains('has-img') && !e.target.closest('button')) input.click();
    });
    ['dragenter', 'dragover'].forEach((ev) => zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.add('dragover');
    }));
    ['dragleave', 'drop'].forEach((ev) => zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
    }));
    zone.addEventListener('drop', (e) => {
      takeFile(n, e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]);
    });

    $('#confirm-' + n).addEventListener('click', () => confirmPick(n));
  }

  // 사진을 칸 밖에 놓쳐도 브라우저가 그 사진을 열어 버리지 않게 막는다
  ['dragover', 'drop'].forEach((ev) => window.addEventListener(ev, (e) => {
    if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files')) e.preventDefault();
  }));

  function enterPick(n) {
    const cur = n === 1 ? state.obj : state.bg;
    if (cur) {
      showPreview(n, cur.src, $('#samples-' + n + ' [data-src="' + cur.src + '"]'));
    }
  }

  async function confirmPick(n) {
    const src = pending[n];
    if (!src) return;
    $('#confirm-' + n).hidden = true;
    const img = await loadImage(src);
    const key = n === 1 ? 'obj' : 'bg';
    const changed = !state[key] || state[key].src !== src;
    state[key] = { img, src };
    if (changed) {
      if (n === 1) {
        state.cutout = null;
        state.done[3] = false;
        s3.src = null;
        $('#slot-3').innerHTML = '<em>추출 전</em>';
      } else {
        s4.src = null;
      }
    }
    state.done[n] = true;
    await fly($('#pv-' + n + ' img'), $('#slot-' + n), () => setSlotImg(n, src));
    go(n + 1);
  }

  initPick(1);
  initPick(2);

  /* ---------- 3단계: 점 찍기로 객체 추출 ---------- */
  const c3 = $('#c3');
  const s3 = { src: null, w: 0, h: 0, work: null, mask: null, pts: [], hist: [], dw: 0, dh: 0 };
  const R_POS = 0.2;
  const R_NEG = 0.1;

  function rebuildMask(s) {
    const ctx = s.mask.getContext('2d');
    ctx.clearRect(0, 0, s.w, s.h);
    const base = Math.min(s.w, s.h);
    s.pts.forEach((p) => {
      ctx.globalCompositeOperation = p.neg ? 'destination-out' : 'source-over';
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.arc(p.x * s.w, p.y * s.h, base * (p.neg ? R_NEG : R_POS), 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalCompositeOperation = 'source-over';
  }

  function posBBox(s) {
    const base = Math.min(s.w, s.h) * R_POS;
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    s.pts.filter((p) => !p.neg).forEach((p) => {
      x1 = Math.min(x1, p.x * s.w - base);
      y1 = Math.min(y1, p.y * s.h - base);
      x2 = Math.max(x2, p.x * s.w + base);
      y2 = Math.max(y2, p.y * s.h + base);
    });
    if (x1 === Infinity) return null;
    x1 = Math.max(0, x1); y1 = Math.max(0, y1);
    x2 = Math.min(s.w, x2); y2 = Math.min(s.h, y2);
    return { x: x1, y: y1, w: Math.max(1, x2 - x1), h: Math.max(1, y2 - y1) };
  }

  function paintTint(ctx, mask, dw, dh, color) {
    const tmp = document.createElement('canvas');
    tmp.width = dw;
    tmp.height = dh;
    const t = tmp.getContext('2d');
    t.drawImage(mask, 0, 0, dw, dh);
    t.globalCompositeOperation = 'source-in';
    t.fillStyle = color;
    t.fillRect(0, 0, dw, dh);
    ctx.drawImage(tmp, 0, 0);
  }

  function drawDot(ctx, x, y, color) {
    ctx.beginPath();
    ctx.arc(x, y, 8, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#fff';
    ctx.stroke();
  }

  function render3() {
    const ctx = c3.getContext('2d');
    ctx.clearRect(0, 0, s3.dw, s3.dh);
    ctx.drawImage(s3.work, 0, 0, s3.dw, s3.dh);
    paintTint(ctx, s3.mask, s3.dw, s3.dh, 'rgba(125, 26, 36, 0.5)');
    s3.pts.forEach((p) => drawDot(ctx, p.x * s3.dw, p.y * s3.dh, p.neg ? '#e11d48' : '#16171b'));
    const pos = s3.pts.filter((p) => !p.neg).length;
    const neg = s3.pts.length - pos;
    $('#c3-count').textContent = '찍은 점 ' + s3.pts.length + '개' + (neg ? ' (제외 ' + neg + ')' : '');
    $('#confirm-3').disabled = pos === 0;
    $('#c3-undo').disabled = !s3.hist.length;
  }

  async function enterStep3() {
    const has = !!state.obj;
    c3.hidden = !has;
    $('#c3-empty').hidden = has;
    $('#confirm-3').disabled = true;
    $('#c3-undo').disabled = true;
    if (!has) return;
    if (s3.src !== state.obj.src) {
      const w = makeWork(state.obj.img);
      s3.src = state.obj.src;
      s3.work = w.work; s3.w = w.w; s3.h = w.h;
      s3.mask = document.createElement('canvas');
      s3.mask.width = w.w; s3.mask.height = w.h;
      s3.pts = [];
      s3.hist = [];
    }
    const d = boxFit(c3, s3.w, s3.h);
    s3.dw = d.w; s3.dh = d.h;
    c3.width = d.w; c3.height = d.h;
    render3();
  }

  function pointer(e, canvas) {
    const r = canvas.getBoundingClientRect();
    return { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height, px: e.clientX - r.left, py: e.clientY - r.top };
  }

  // 되돌리기: 바꾸기 직전의 점 목록을 쌓아 두고 하나씩 꺼내 복원한다 (최대 50단계)
  function pushHist3() {
    s3.hist.push(s3.pts.map((q) => ({ x: q.x, y: q.y, neg: q.neg })));
    if (s3.hist.length > 50) s3.hist.shift();
  }

  c3.addEventListener('contextmenu', (e) => e.preventDefault());
  c3.addEventListener('mousedown', (e) => {
    if (!s3.work) return;
    const p = pointer(e, c3);
    const hit = s3.pts.findIndex((q) => Math.hypot(q.x * s3.dw - p.px, q.y * s3.dh - p.py) < 11);
    pushHist3();
    if (hit >= 0) {
      s3.pts.splice(hit, 1);
    } else {
      s3.pts.push({ x: p.x, y: p.y, neg: e.button === 2 });
    }
    rebuildMask(s3);
    render3();
  });
  $('#c3-reset').addEventListener('click', () => {
    if (!s3.work || !s3.pts.length) return;
    pushHist3();
    s3.pts = [];
    rebuildMask(s3);
    render3();
  });
  $('#c3-undo').addEventListener('click', () => {
    if (!s3.work || !s3.hist.length) return;
    s3.pts = s3.hist.pop();
    rebuildMask(s3);
    render3();
  });

  $('#confirm-3').addEventListener('click', async () => {
    const bb = posBBox(s3);
    if (!bb) return;
    const cut = document.createElement('canvas');
    cut.width = s3.w; cut.height = s3.h;
    const cx = cut.getContext('2d');
    cx.drawImage(s3.work, 0, 0);
    cx.globalCompositeOperation = 'destination-in';
    cx.drawImage(s3.mask, 0, 0);
    state.cutout = { canvas: cut, bbox: bb };
    state.done[3] = true;
    await fly(c3, $('#slot-3'), () => {
      const slot = $('#slot-3');
      const sc = document.createElement('canvas');
      sc.width = 480; sc.height = 300;
      drawContain(sc.getContext('2d'), cut, bb.x, bb.y, bb.w, bb.h, 480, 300);
      slot.innerHTML = '';
      slot.appendChild(sc);
    });
    go(4);
  });

  /* ---------- 4단계: 합성 영역 지정 (점 + 브러시) ---------- */
  const c4 = $('#c4');
  const s4 = { src: null, w: 0, h: 0, work: null, mask: null, dots: [], bbox: null, touched: false, hist: [], dw: 0, dh: 0 };
  let tool = 'point';
  let painting = false;
  let last = null;

  function growBBox(x, y, r) {
    const b = s4.bbox || { x1: Infinity, y1: Infinity, x2: -Infinity, y2: -Infinity };
    b.x1 = Math.min(b.x1, x - r); b.y1 = Math.min(b.y1, y - r);
    b.x2 = Math.max(b.x2, x + r); b.y2 = Math.max(b.y2, y + r);
    s4.bbox = b;
  }

  function bboxRect() {
    const b = s4.bbox;
    if (!b) return null;
    const x = Math.max(0, b.x1), y = Math.max(0, b.y1);
    return { x, y, w: Math.max(1, Math.min(s4.w, b.x2) - x), h: Math.max(1, Math.min(s4.h, b.y2) - y) };
  }

  function render4() {
    const ctx = c4.getContext('2d');
    ctx.clearRect(0, 0, s4.dw, s4.dh);
    ctx.drawImage(s4.work, 0, 0, s4.dw, s4.dh);
    paintTint(ctx, s4.mask, s4.dw, s4.dh, 'rgba(31, 81, 56, 0.55)');
    s4.dots.forEach((p) => drawDot(ctx, p.x * s4.dw, p.y * s4.dh, '#16171b'));
    $('#confirm-4').disabled = !s4.touched;
    $('#c4-undo').disabled = !s4.hist.length;
  }

  function enterStep4() {
    const has = !!state.bg;
    c4.hidden = !has;
    $('#c4-empty').hidden = has;
    $('#confirm-4').disabled = true;
    $('#c4-undo').disabled = true;
    if (!has) return;
    if (s4.src !== state.bg.src) {
      const w = makeWork(state.bg.img);
      s4.src = state.bg.src;
      s4.work = w.work; s4.w = w.w; s4.h = w.h;
      s4.mask = document.createElement('canvas');
      s4.mask.width = w.w; s4.mask.height = w.h;
      s4.dots = []; s4.bbox = null; s4.touched = false;
      s4.hist = [];
    }
    const d = boxFit(c4, s4.w, s4.h);
    s4.dw = d.w; s4.dh = d.h;
    c4.width = d.w; c4.height = d.h;
    render4();
  }

  function brushPx() {
    return Number($('#brush-size').value) * (s4.w / s4.dw);
  }

  function stroke(from, to) {
    const ctx = s4.mask.getContext('2d');
    const r = brushPx() / 2;
    ctx.globalCompositeOperation = tool === 'eraser' ? 'destination-out' : 'source-over';
    ctx.strokeStyle = '#fff';
    ctx.fillStyle = '#fff';
    ctx.lineCap = 'round';
    ctx.lineWidth = r * 2;
    ctx.beginPath();
    ctx.moveTo(from.x * s4.w, from.y * s4.h);
    ctx.lineTo(to.x * s4.w, to.y * s4.h);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(to.x * s4.w, to.y * s4.h, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
    if (tool === 'brush') {
      growBBox(to.x * s4.w, to.y * s4.h, r);
      growBBox(from.x * s4.w, from.y * s4.h, r);
      s4.touched = true;
    }
  }

  // 되돌리기: 칠하기 직전의 영역(마스크, 점, 범위)을 통째로 쌓아 두고 하나씩 꺼내 복원한다 (최대 20단계)
  function pushHist4() {
    const snap = document.createElement('canvas');
    snap.width = s4.w; snap.height = s4.h;
    snap.getContext('2d').drawImage(s4.mask, 0, 0);
    s4.hist.push({
      mask: snap,
      dots: s4.dots.map((d) => ({ x: d.x, y: d.y })),
      bbox: s4.bbox ? { x1: s4.bbox.x1, y1: s4.bbox.y1, x2: s4.bbox.x2, y2: s4.bbox.y2 } : null,
      touched: s4.touched,
    });
    if (s4.hist.length > 20) s4.hist.shift();
  }

  c4.addEventListener('mousedown', (e) => {
    if (!s4.work) return;
    const p = pointer(e, c4);
    // 점, 브러시는 항상, 지우개는 지울 것이 있을 때만 한 번의 동작(드래그 한 번)을 한 단계로 기록한다
    if (tool !== 'eraser' || s4.touched) pushHist4();
    if (tool === 'point') {
      const ctx = s4.mask.getContext('2d');
      const r = Math.min(s4.w, s4.h) * 0.17;
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.arc(p.x * s4.w, p.y * s4.h, r, 0, Math.PI * 2);
      ctx.fill();
      growBBox(p.x * s4.w, p.y * s4.h, r);
      s4.dots.push({ x: p.x, y: p.y });
      s4.touched = true;
      render4();
      return;
    }
    painting = true;
    last = p;
    stroke(p, p);
    render4();
  });
  c4.addEventListener('mousemove', (e) => {
    if (!painting) return;
    const p = pointer(e, c4);
    stroke(last, p);
    last = p;
    render4();
  });
  ['mouseup', 'mouseleave'].forEach((ev) => c4.addEventListener(ev, () => { painting = false; }));

  $$('#sg-tools .sg-tool').forEach((b) => {
    b.addEventListener('click', () => {
      tool = b.dataset.tool;
      $$('#sg-tools .sg-tool').forEach((x) => x.classList.toggle('active', x === b));
    });
  });

  $('#c4-reset').addEventListener('click', () => {
    if (!s4.work) return;
    if (s4.touched) pushHist4();
    s4.mask.getContext('2d').clearRect(0, 0, s4.w, s4.h);
    s4.dots = []; s4.bbox = null; s4.touched = false;
    render4();
  });
  $('#c4-undo').addEventListener('click', () => {
    if (!s4.work || !s4.hist.length) return;
    const h = s4.hist.pop();
    const ctx = s4.mask.getContext('2d');
    ctx.clearRect(0, 0, s4.w, s4.h);
    ctx.drawImage(h.mask, 0, 0);
    s4.dots = h.dots; s4.bbox = h.bbox; s4.touched = h.touched;
    render4();
  });

  /* ---------- 합성 (시안) ---------- */
  function compose() {
    const out = document.createElement('canvas');
    out.width = s4.w; out.height = s4.h;
    const ctx = out.getContext('2d');
    ctx.drawImage(s4.work, 0, 0);

    const mb = bboxRect();
    const cb = state.cutout.bbox;
    const tmp = document.createElement('canvas');
    tmp.width = s4.w; tmp.height = s4.h;
    const t = tmp.getContext('2d');
    // 추출한 상의를 합성 영역에 가득 차도록 맞춰 붙인 뒤, 지정한 영역 모양으로 잘라낸다
    const sc = Math.max(mb.w / cb.w, mb.h / cb.h);
    const dw = cb.w * sc;
    const dh = cb.h * sc;
    t.drawImage(state.cutout.canvas, cb.x, cb.y, cb.w, cb.h, mb.x + (mb.w - dw) / 2, mb.y + (mb.h - dh) / 2, dw, dh);
    t.globalCompositeOperation = 'destination-in';
    t.drawImage(s4.mask, 0, 0);
    ctx.globalAlpha = 0.96;
    ctx.drawImage(tmp, 0, 0);
    ctx.globalAlpha = 1;
    return out;
  }

  $('#confirm-4').addEventListener('click', () => {
    if (!s4.touched || !state.cutout) return;
    $('#sg-busy').classList.add('show');
    setTimeout(async () => {
      state.result = compose();
      state.saved = false;
      await showResult({ canvas: state.result }, false);
      $('#sg-busy').classList.remove('show');
    }, 3200);
  });

  /* ---------- 결과, 저장, 작업 기록 ---------- */
  const cRes = $('#c-result');
  const btnSave = $('#btn-save');
  const btnRedo = $('#btn-redo');
  let viewingHistory = false;

  let lastEntry = null;
  async function showResult(entry, fromHistory) {
    viewingHistory = fromHistory;
    lastEntry = entry;
    await go('result');
    let w, h, src;
    if (entry.canvas) { src = entry.canvas; w = entry.canvas.width; h = entry.canvas.height; }
    else { src = await loadImage(entry.src); w = src.naturalWidth; h = src.naturalHeight; }
    const d = boxFit(cRes, w, h);
    cRes.width = d.w; cRes.height = d.h;
    cRes.getContext('2d').drawImage(src, 0, 0, d.w, d.h);

    $('#result-title').textContent = fromHistory ? '저장된 결과' : '합성 결과';
    btnSave.hidden = false;
    btnSave.disabled = fromHistory || state.saved;
    btnSave.textContent = fromHistory || state.saved ? '저장됨' : '저장하기';
    btnRedo.textContent = fromHistory ? '새로 합성하기' : '다시하기';
  }

  function addHistory(entry, d, isNew) {
    const list = $('#sg-history');
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'sg-hist-item';
    const thumb = document.createElement('div');
    thumb.className = 'sg-hist-thumb';
    if (entry.canvas) {
      const c = document.createElement('canvas');
      c.width = 400; c.height = 300;
      drawCover(c.getContext('2d'), entry.canvas, 0, 0, entry.canvas.width, entry.canvas.height, 400, 300);
      thumb.appendChild(c);
    } else {
      thumb.innerHTML = '<img src="' + entry.src + '" alt="">';
    }
    if (isNew) {
      const badge = document.createElement('span');
      badge.className = 'sg-hist-new';
      badge.textContent = 'NEW';
      thumb.appendChild(badge);
    }
    const date = document.createElement('span');
    date.className = 'sg-hist-date';
    date.textContent = d;
    // 왼쪽 진행 상황처럼 위에 이름(여기서는 생성 날짜), 아래에 사진
    item.appendChild(date);
    item.appendChild(thumb);
    item.addEventListener('click', () => {
      $$('.sg-hist-item').forEach((x) => x.classList.toggle('active', x === item));
      showResult(entry, true);
    });
    if (isNew) { item.classList.add('sg-hist-fresh'); list.insertBefore(item, list.firstChild); } else list.appendChild(item);
    syncHistoryScrollbar();
  }

  // 스크롤바가 보이는 만큼 목록을 오른쪽으로 넓혀서, 사진 폭이 왼쪽 진행 상황의 사진과 같아지게 한다
  function syncHistoryScrollbar() {
    const h = $('#sg-history');
    h.style.marginRight = '0px';
    const sb = h.offsetWidth - h.clientWidth;
    h.style.marginRight = (-sb) + 'px';
  }

  function nowText() {
    const n = new Date();
    const p = (v) => String(v).padStart(2, '0');
    return n.getFullYear() + '.' + p(n.getMonth() + 1) + '.' + p(n.getDate()) + ' ' + p(n.getHours()) + ':' + p(n.getMinutes());
  }

  btnSave.addEventListener('click', () => {
    if (viewingHistory || state.saved || !state.result) return;
    state.saved = true;
    addHistory({ canvas: state.result }, nowText(), true);
    btnSave.disabled = true;
    btnSave.textContent = '저장됨';
    toast('내 작업 기록에 저장했습니다');
  });

  btnRedo.addEventListener('click', () => {
    if (viewingHistory) {
      go(1);
    } else {
      go(4);
    }
  });

  HISTORY.forEach((h) => addHistory({ src: h.src }, h.d, false));

  // 창 크기가 바뀌면 캔버스를 칸에 다시 맞춘다
  let resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      syncHistoryScrollbar();
      if (state.step === 3) enterStep3();
      else if (state.step === 4) enterStep4();
      else if (state.step === 'result' && lastEntry) showResult(lastEntry, viewingHistory);
    }, 150);
  });

  applyStep(0);
})();
