/* 합성하기 화면의 그리기 도우미 (화면 상태와 무관한 순수 함수들) */

export function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

export function newCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

// 작업용 사본: 긴 변을 1000px 이하로 줄인 캔버스
export function makeWork(img) {
  const sc = Math.min(1, 1000 / Math.max(img.naturalWidth, img.naturalHeight));
  const w = Math.round(img.naturalWidth * sc);
  const h = Math.round(img.naturalHeight * sc);
  const c = newCanvas(w, h);
  c.getContext('2d').drawImage(img, 0, 0, w, h);
  return { work: c, w, h };
}

function fit(w, h, maxW, maxH) {
  const sc = Math.min(maxW / w, maxH / h, 1);
  return { w: Math.round(w * sc), h: Math.round(h * sc) };
}

// 캔버스를 둘러싼 칸의 남는 공간에 맞춰 크기를 정한다 (한 화면 고정이라 페이지가 늘어나지 않는다)
export function boxFit(canvas, w, h) {
  const box = canvas.parentElement;
  const cs = getComputedStyle(box);
  const aw = box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const ah = box.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  return fit(w, h, Math.max(160, aw), Math.max(160, ah));
}

// 원본 영역(sx, sy, sw, sh)을 비율을 유지하며 dw x dh 가득 채워 그린다
export function drawCover(ctx, src, sx, sy, sw, sh, dw, dh) {
  const sc = Math.max(dw / sw, dh / sh);
  const w = sw * sc;
  const h = sh * sc;
  ctx.drawImage(src, sx, sy, sw, sh, (dw - w) / 2, (dh - h) / 2, w, h);
}

export function drawContain(ctx, src, sx, sy, sw, sh, dw, dh) {
  const sc = Math.min(dw / sw, dh / sh);
  const w = sw * sc;
  const h = sh * sc;
  ctx.drawImage(src, sx, sy, sw, sh, (dw - w) / 2, (dh - h) / 2, w, h);
}

// 마스크 모양대로 반투명 색을 덮는다
export function paintTint(ctx, mask, dw, dh, color) {
  const tmp = newCanvas(dw, dh);
  const t = tmp.getContext('2d');
  t.drawImage(mask, 0, 0, dw, dh);
  t.globalCompositeOperation = 'source-in';
  t.fillStyle = color;
  t.fillRect(0, 0, dw, dh);
  ctx.drawImage(tmp, 0, 0);
}

export function drawDot(ctx, x, y, color) {
  ctx.beginPath();
  ctx.arc(x, y, 8, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = '#fff';
  ctx.stroke();
}

// 마스크에서 칠해진 부분을 감싸는 사각형. 칠한 곳이 없으면 null
export function maskBBox(mask) {
  const { width: w, height: h } = mask;
  const d = mask.getContext('2d').getImageData(0, 0, w, h).data;
  let x1 = w; let y1 = h; let x2 = -1; let y2 = -1;
  for (let y = 0; y < h; y += 1) {
    for (let x = 0; x < w; x += 1) {
      if (d[(y * w + x) * 4 + 3] > 0) {
        if (x < x1) x1 = x;
        if (x > x2) x2 = x;
        if (y < y1) y1 = y;
        if (y > y2) y2 = y;
      }
    }
  }
  if (x2 < 0) return null;
  return { x: x1, y: y1, w: x2 - x1 + 1, h: y2 - y1 + 1 };
}

// 마우스 위치: 0~1 비율(x, y)과 캔버스 안 픽셀 위치(px, py)
export function pointer(e, canvas) {
  const r = canvas.getBoundingClientRect();
  return { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height, px: e.clientX - r.left, py: e.clientY - r.top };
}

export function nowText() {
  const n = new Date();
  const p = (v) => String(v).padStart(2, '0');
  return n.getFullYear() + '.' + p(n.getMonth() + 1) + '.' + p(n.getDate()) + ' ' + p(n.getHours()) + ':' + p(n.getMinutes());
}

// 선택한 사진이 작아지면서 왼쪽 칸으로 이동하는 효과. 끝나면 finish()로 칸 내용을 바꾼다.
export function fly(fromEl, toEl, finish) {
  return new Promise((resolve) => {
    if (!fromEl || !toEl) { finish(); resolve(); return; }
    const r1 = fromEl.getBoundingClientRect();
    const r2 = toEl.getBoundingClientRect();
    // 왼쪽 패널이 접혀 있어 목적지 칸이 보이지 않으면 날아가는 효과만 건너뛰고 결과는 그대로 반영한다
    if (!r2.width || !r2.height) { finish(); resolve(); return; }
    let clone;
    if (fromEl instanceof HTMLCanvasElement) {
      clone = newCanvas(fromEl.width, fromEl.height);
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
