/* 다듬기 팝업: 점 찍기로 잡은 영역을 브러시(추가)와 지우개(삭제)로 손본다. 3단계(상의 추출)와 4단계(합성 영역)가 같이 쓴다.
   image: 작업용 사진 캔버스, mask: 시작할 영역(흰색 캔버스). 원본은 건드리지 않고 사본을 고쳐서 onDone으로 돌려준다.
   영역은 포토샵 선택 영역처럼 보여 준다: 안쪽은 움직이는 검정·흰색 빗금, 가장자리는 움직이는 흑백 점선 (canvas.js paintSelection).
   확대 보기, 10/21: zoom.js와 같은 보기 상태 사용. 휠·＋/－ 버튼으로 확대, 스페이스바를 누른 채 끌거나 오른쪽·가운데 버튼으로 끌면 이동.
   브러시 크기는 화면 기준이라 확대할수록 사진에는 더 가늘게 칠해진다. */
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { boxFit, buildSelection, newCanvas, paintSelection, pointer } from './canvas.js';
import { drawView, fullView, zoomAt } from './zoom.js';

const MAX_HISTORY = 20;

// 마스크에 칠해진 곳이 있는지
function hasPaint(mask) {
  const d = mask.getContext('2d').getImageData(0, 0, mask.width, mask.height).data;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 0) return true;
  return false;
}

export default function MaskEditor({ title, help, image, mask, cancelLabel, doneLabel, onCancel, onDone }) {
  const canvasRef = useRef(null);
  const ed = useRef({ mask: null, vmask: null, sel: null, w: 0, h: 0, dw: 0, dh: 0, hist: [] });
  const view = useRef(fullView()); // 확대 보기 상태 { z, x0, y0 }
  const pan = useRef(null); // 끌어서 이동 중: { x, y, view }
  const spaceDown = useRef(false);
  const [zoom, setZoom] = useState(1);
  const [panning, setPanning] = useState(false);
  const phase = useRef(0); // 무늬가 움직인 거리 (px)
  const renderRef = useRef(null);
  const toolRef = useRef('brush');
  const sizeRef = useRef(40);
  const painting = useRef(false);
  const last = useRef(null);
  const [tool, setTool] = useState('brush');
  const [size, setSize] = useState(40);
  const [canUndo, setCanUndo] = useState(false);
  const [empty, setEmpty] = useState(false);
  const [ring, setRing] = useState(null); // 브러시 크기 동그라미 위치

  const render = () => {
    const s = ed.current;
    if (!canvasRef.current || !s.sel) return;
    const ctx = canvasRef.current.getContext('2d');
    ctx.clearRect(0, 0, s.dw, s.dh);
    drawView(ctx, image, s.w, s.h, s.dw, s.dh, view.current);
    paintSelection(ctx, s.sel, phase.current);
  };
  renderRef.current = render;

  // 영역이 바뀌었을 때(칠하기, 지우기, 실행 취소, 크기 변경, 확대·이동) 보이는 부분의 표시용 모양을 다시 만든다
  const rebuild = () => {
    const s = ed.current;
    if (!s.vmask || s.vmask.width !== s.dw || s.vmask.height !== s.dh) s.vmask = newCanvas(s.dw, s.dh);
    const vctx = s.vmask.getContext('2d');
    vctx.clearRect(0, 0, s.dw, s.dh);
    drawView(vctx, s.mask, s.w, s.h, s.dw, s.dh, view.current);
    s.sel = buildSelection(s.vmask, s.dw, s.dh, s.sel);
    render();
  };

  const setViewTo = (v) => {
    view.current = v;
    setZoom(v.z);
    rebuild();
  };
  // 화면의 (fx, fy) 지점(0~1)을 중심으로 확대·축소
  const zoomBy = (factor, fx = 0.5, fy = 0.5) => setViewTo(zoomAt(view.current, fx, fy, factor));

  // 캔버스 위치(0~1) → 사진 위치(0~1)
  const toImage = (p) => {
    const v = view.current;
    return { x: v.x0 + p.x / v.z, y: v.y0 + p.y / v.z };
  };

  const fitCanvas = () => {
    const s = ed.current;
    const d = boxFit(canvasRef.current, s.w, s.h);
    s.dw = d.w; s.dh = d.h;
    canvasRef.current.width = d.w; canvasRef.current.height = d.h;
    rebuild();
  };

  // 무늬를 움직인다 (초당 약 30번). 움직임 줄이기 설정이면 멈춘 무늬로 둔다
  useEffect(() => {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    let id;
    let lastDraw = 0;
    const tick = (now) => {
      if (now - lastDraw > 33) {
        lastDraw = now;
        phase.current = now / 60;
        renderRef.current();
      }
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, []);

  // 팝업이 열릴 때 받은 영역을 복사해서 시작한다
  useLayoutEffect(() => {
    const s = ed.current;
    s.w = image.width; s.h = image.height;
    s.mask = newCanvas(s.w, s.h);
    s.mask.getContext('2d').drawImage(mask, 0, 0, s.w, s.h);
    s.hist = [];
    view.current = fullView();
    setZoom(1);
    setCanUndo(false);
    setEmpty(!hasPaint(s.mask));
    fitCanvas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [image, mask]);

  useEffect(() => {
    let t = null;
    const onResize = () => { clearTimeout(t); t = setTimeout(fitCanvas, 150); };
    const onKey = (e) => {
      if (e.key === 'Escape') onCancel();
      if (e.code === 'Space') { e.preventDefault(); spaceDown.current = true; } // 스페이스바를 누른 채 끌면 이동
    };
    const onKeyUp = (e) => { if (e.code === 'Space') spaceDown.current = false; };
    window.addEventListener('resize', onResize);
    document.addEventListener('keydown', onKey);
    document.addEventListener('keyup', onKeyUp);
    return () => {
      clearTimeout(t);
      window.removeEventListener('resize', onResize);
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('keyup', onKeyUp);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onCancel]);

  // 휠 확대: 가리킨 곳을 중심으로. 페이지가 스크롤되지 않게 passive: false로 직접 붙인다
  useEffect(() => {
    const c = canvasRef.current;
    const onWheel = (e) => {
      e.preventDefault();
      const r = c.getBoundingClientRect();
      zoomBy(e.deltaY < 0 ? 1.25 : 1 / 1.25, (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
    };
    c.addEventListener('wheel', onWheel, { passive: false });
    return () => c.removeEventListener('wheel', onWheel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stroke = (from, to) => {
    const s = ed.current;
    const ctx = s.mask.getContext('2d');
    const r = (sizeRef.current * (s.w / s.dw)) / view.current.z / 2; // 화면에 보이는 브러시 크기 그대로
    ctx.globalCompositeOperation = toolRef.current === 'eraser' ? 'destination-out' : 'source-over';
    ctx.strokeStyle = '#fff';
    ctx.fillStyle = '#fff';
    ctx.lineCap = 'round';
    ctx.lineWidth = r * 2;
    ctx.beginPath();
    ctx.moveTo(from.x * s.w, from.y * s.h);
    ctx.lineTo(to.x * s.w, to.y * s.h);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(to.x * s.w, to.y * s.h, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
  };

  // 되돌리기: 칠하기 직전의 영역을 쌓아 두고 하나씩 꺼낸다
  const pushHist = () => {
    const s = ed.current;
    const snap = newCanvas(s.w, s.h);
    snap.getContext('2d').drawImage(s.mask, 0, 0);
    s.hist.push(snap);
    if (s.hist.length > MAX_HISTORY) s.hist.shift();
    setCanUndo(true);
  };

  const moveRing = (e) => {
    const r = canvasRef.current.getBoundingClientRect();
    const box = canvasRef.current.parentElement.getBoundingClientRect();
    setRing({ left: e.clientX - box.left, top: e.clientY - box.top, inside: e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom });
  };

  const onDown = (e) => {
    // 오른쪽·가운데 버튼, 또는 스페이스바를 누른 채 끌면 칠하지 않고 이동
    if (e.button === 1 || e.button === 2 || spaceDown.current) {
      e.preventDefault();
      pan.current = { x: e.clientX, y: e.clientY, view: view.current };
      setPanning(true);
      return;
    }
    if (e.button !== 0) return;
    pushHist();
    const p = toImage(pointer(e, canvasRef.current));
    painting.current = true;
    last.current = p;
    stroke(p, p);
    rebuild();
  };
  const onMove = (e) => {
    if (pan.current) {
      const r = canvasRef.current.getBoundingClientRect();
      const st = pan.current;
      const moved = { ...st.view, x0: st.view.x0 - (e.clientX - st.x) / r.width / st.view.z, y0: st.view.y0 - (e.clientY - st.y) / r.height / st.view.z };
      setViewTo(zoomAt(moved, 0, 0, 1)); // 배율 그대로, 사진 밖이 보이지 않게 위치만 맞춤
      return;
    }
    moveRing(e);
    if (!painting.current) return;
    const p = toImage(pointer(e, canvasRef.current));
    stroke(last.current, p);
    last.current = p;
    rebuild();
  };
  const endPaint = () => {
    if (pan.current) { pan.current = null; setPanning(false); }
    if (!painting.current) return;
    painting.current = false;
    setEmpty(!hasPaint(ed.current.mask));
  };

  const undo = () => {
    const s = ed.current;
    if (!s.hist.length) return;
    const snap = s.hist.pop();
    const ctx = s.mask.getContext('2d');
    ctx.clearRect(0, 0, s.w, s.h);
    ctx.drawImage(snap, 0, 0);
    setCanUndo(s.hist.length > 0);
    setEmpty(!hasPaint(s.mask));
    rebuild();
  };

  const chooseTool = (t) => { toolRef.current = t; setTool(t); };
  const changeSize = (v) => { sizeRef.current = v; setSize(v); };

  return (
    <div className="sg-modal" role="dialog" aria-modal="true" aria-label={title}>
      <div className="sg-modal-box sg-modal-wide">
        <div className="sg-modal-head">
          <h3>{title}</h3>
          <button type="button" className="sg-modal-close" aria-label="닫기" onClick={onCancel}>×</button>
        </div>
        <div className="sg-help"><b>사용 방법</b><p>{help}</p></div>
        <div className="sg-tools">
          <button type="button" className={'sg-tool' + (tool === 'brush' ? ' active' : '')} onClick={() => chooseTool('brush')}>브러시</button>
          <button type="button" className={'sg-tool' + (tool === 'eraser' ? ' active' : '')} onClick={() => chooseTool('eraser')}>지우개</button>
          <label className="sg-size">크기 <input type="range" min="10" max="90" value={size} onChange={(e) => changeSize(Number(e.target.value))} /></label>
        </div>
        <div className="sg-canvas-box" onMouseLeave={() => setRing(null)}>
          <div className="sg-zoom" role="group" aria-label="사진 확대">
            <button type="button" aria-label="확대" onClick={() => zoomBy(1.5)}>＋</button>
            <span>{Math.round(zoom * 100)}%</span>
            <button type="button" aria-label="축소" disabled={zoom <= 1} onClick={() => zoomBy(1 / 1.5)}>－</button>
            <button type="button" disabled={zoom <= 1} onClick={() => setViewTo(fullView())}>전체</button>
          </div>
          <canvas
            ref={canvasRef}
            className={'sg-canvas' + (panning ? ' panning' : '')}
            onMouseDown={onDown}
            onMouseMove={onMove}
            onMouseUp={endPaint}
            onMouseLeave={endPaint}
            onContextMenu={(e) => e.preventDefault()}
          />
          {ring && ring.inside && !panning && <span className="sg-brush-ring" style={{ left: ring.left, top: ring.top, width: size, height: size }} />}
        </div>
        <p className="sg-zoom-hint">휠로 확대, 스페이스바를 누른 채 끌거나 오른쪽 버튼으로 끌면 이동</p>
        <div className="sg-actions">
          <button type="button" className="sg-ghost" disabled={!canUndo} onClick={undo}>실행 취소</button>
          <button type="button" className="sg-ghost" onClick={onCancel}>{cancelLabel}</button>
          <button type="button" className="sg-confirm" disabled={empty} onClick={() => onDone(ed.current.mask)}>{doneLabel}</button>
        </div>
      </div>
    </div>
  );
}
