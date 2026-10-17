/* 3·4단계 점 찍기 화면의 확대 보기.
   - 확대: 마우스 휠(가리킨 곳을 중심으로), 휴대폰은 두 손가락 벌리기, 화면의 ＋/－ 버튼
   - 이동: 확대한 상태에서 끌기
   - 점 찍기: 끌지 않고 누르기만 하면 onTap (오른쪽 버튼이면 제외 점)
   보기 상태 view = { z: 배율, x0, y0: 화면 왼쪽 위가 가리키는 사진 위치 }. 좌표는 모두 사진 기준 0~1. */

export const ZOOM_MAX = 6;
const DRAG_PX = 5; // 이만큼 움직이면 점 찍기가 아니라 끌기로 본다

export const fullView = () => ({ z: 1, x0: 0, y0: 0 });

// 사진 밖이 보이지 않게 위치를 맞춘다
function clampView(v) {
  const z = Math.min(Math.max(v.z, 1), ZOOM_MAX);
  const span = 1 / z;
  return { z, x0: Math.min(Math.max(v.x0, 0), 1 - span), y0: Math.min(Math.max(v.y0, 0), 1 - span) };
}

// 화면의 (fx, fy) 지점(0~1)이 가리키는 사진 위치를 그대로 두고 factor배 확대/축소
export function zoomAt(v, fx, fy, factor) {
  const z = Math.min(Math.max(v.z * factor, 1), ZOOM_MAX);
  const ix = v.x0 + fx / v.z;
  const iy = v.y0 + fy / v.z;
  return clampView({ z, x0: ix - fx / z, y0: iy - fy / z });
}

// 보이는 부분만 캔버스 가득 그린다
export function drawView(ctx, img, w, h, dw, dh, v) {
  ctx.drawImage(img, v.x0 * w, v.y0 * h, w / v.z, h / v.z, 0, 0, dw, dh);
}

// 사진 위치(0~1) → 캔버스 위치(px)
export const toCanvas = (v, p, dw, dh) => ({ x: (p.x - v.x0) * v.z * dw, y: (p.y - v.y0) * v.z * dh });

// 캔버스에 확대·이동·누르기를 붙이고, 떼는 함수를 돌려준다
// getView/setView: 보기 상태 읽기·바꾸기, redraw: 다시 그리기, onTap({ x, y, px, py }, neg): 점 찍기
export function attachZoom(canvas, { getView, setView, redraw, onTap }) {
  const pointers = new Map();
  let start = null; // 한 손가락(또는 마우스) 누름: { x, y, view, moved, button }
  let pinch = null; // 두 손가락: { d, view }

  const rect = () => canvas.getBoundingClientRect();
  const apply = (v) => { setView(v); redraw(); };

  const onWheel = (e) => {
    e.preventDefault(); // 페이지가 스크롤되지 않게
    const r = rect();
    apply(zoomAt(getView(), (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height, e.deltaY < 0 ? 1.25 : 1 / 1.25));
  };

  const onDown = (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, view: getView() };
      start = null;
      return;
    }
    start = { x: e.clientX, y: e.clientY, view: getView(), moved: false, button: e.button };
  };

  const onMove = (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const r = rect();
    if (pinch && pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const mx = ((a.x + b.x) / 2 - r.left) / r.width;
      const my = ((a.y + b.y) / 2 - r.top) / r.height;
      apply(zoomAt(pinch.view, mx, my, Math.hypot(a.x - b.x, a.y - b.y) / pinch.d));
      return;
    }
    if (!start) return;
    const dx = e.clientX - start.x;
    const dy = e.clientY - start.y;
    if (!start.moved && Math.hypot(dx, dy) < DRAG_PX) return;
    start.moved = true;
    if (start.view.z > 1) {
      canvas.style.cursor = 'grabbing';
      apply(clampView({ ...start.view, x0: start.view.x0 - dx / r.width / start.view.z, y0: start.view.y0 - dy / r.height / start.view.z }));
    }
  };

  const onUp = (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.delete(e.pointerId);
    canvas.style.cursor = '';
    if (pinch) {
      if (pointers.size < 2) pinch = null;
      start = null;
      return;
    }
    if (start && !start.moved && e.type === 'pointerup') {
      const r = rect();
      const fx = (e.clientX - r.left) / r.width;
      const fy = (e.clientY - r.top) / r.height;
      const v = getView();
      onTap({ x: v.x0 + fx / v.z, y: v.y0 + fy / v.z, px: fx * r.width, py: fy * r.height }, start.button === 2);
    }
    start = null;
  };

  const noMenu = (e) => e.preventDefault(); // 오른쪽 버튼은 제외 점으로 쓴다
  canvas.addEventListener('wheel', onWheel, { passive: false });
  canvas.addEventListener('pointerdown', onDown);
  canvas.addEventListener('pointermove', onMove);
  canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointercancel', onUp);
  canvas.addEventListener('contextmenu', noMenu);
  return () => {
    canvas.removeEventListener('wheel', onWheel);
    canvas.removeEventListener('pointerdown', onDown);
    canvas.removeEventListener('pointermove', onMove);
    canvas.removeEventListener('pointerup', onUp);
    canvas.removeEventListener('pointercancel', onUp);
    canvas.removeEventListener('contextmenu', noMenu);
  };
}
