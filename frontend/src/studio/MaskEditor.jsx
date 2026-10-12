/* 다듬기 팝업: 점 찍기로 잡은 영역을 브러시(추가)와 지우개(삭제)로 손본다. 3단계(상의 추출)와 4단계(합성 영역)가 같이 쓴다.
   image: 작업용 사진 캔버스, mask: 시작할 영역(흰색 캔버스). 원본은 건드리지 않고 사본을 고쳐서 onDone으로 돌려준다. */
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { boxFit, newCanvas, paintTint, pointer } from './canvas.js';

const MAX_HISTORY = 20;

// 마스크에 칠해진 곳이 있는지
function hasPaint(mask) {
  const d = mask.getContext('2d').getImageData(0, 0, mask.width, mask.height).data;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 0) return true;
  return false;
}

export default function MaskEditor({ title, help, image, mask, tint, cancelLabel, doneLabel, onCancel, onDone }) {
  const canvasRef = useRef(null);
  const ed = useRef({ mask: null, w: 0, h: 0, dw: 0, dh: 0, hist: [] });
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
    const ctx = canvasRef.current.getContext('2d');
    ctx.clearRect(0, 0, s.dw, s.dh);
    ctx.drawImage(image, 0, 0, s.dw, s.dh);
    paintTint(ctx, s.mask, s.dw, s.dh, tint);
  };

  const fitCanvas = () => {
    const s = ed.current;
    const d = boxFit(canvasRef.current, s.w, s.h);
    s.dw = d.w; s.dh = d.h;
    canvasRef.current.width = d.w; canvasRef.current.height = d.h;
    render();
  };

  // 팝업이 열릴 때 받은 영역을 복사해서 시작한다
  useLayoutEffect(() => {
    const s = ed.current;
    s.w = image.width; s.h = image.height;
    s.mask = newCanvas(s.w, s.h);
    s.mask.getContext('2d').drawImage(mask, 0, 0, s.w, s.h);
    s.hist = [];
    setCanUndo(false);
    setEmpty(!hasPaint(s.mask));
    fitCanvas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [image, mask]);

  useEffect(() => {
    let t = null;
    const onResize = () => { clearTimeout(t); t = setTimeout(fitCanvas, 150); };
    const onKey = (e) => { if (e.key === 'Escape') onCancel(); };
    window.addEventListener('resize', onResize);
    document.addEventListener('keydown', onKey);
    return () => { clearTimeout(t); window.removeEventListener('resize', onResize); document.removeEventListener('keydown', onKey); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onCancel]);

  const stroke = (from, to) => {
    const s = ed.current;
    const ctx = s.mask.getContext('2d');
    const r = (sizeRef.current * (s.w / s.dw)) / 2;
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
    pushHist();
    const p = pointer(e, canvasRef.current);
    painting.current = true;
    last.current = p;
    stroke(p, p);
    render();
  };
  const onMove = (e) => {
    moveRing(e);
    if (!painting.current) return;
    const p = pointer(e, canvasRef.current);
    stroke(last.current, p);
    last.current = p;
    render();
  };
  const endPaint = () => {
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
    render();
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
          <canvas
            ref={canvasRef}
            className="sg-canvas"
            onMouseDown={onDown}
            onMouseMove={onMove}
            onMouseUp={endPaint}
            onMouseLeave={endPaint}
          />
          {ring && ring.inside && <span className="sg-brush-ring" style={{ left: ring.left, top: ring.top, width: size, height: size }} />}
        </div>
        <div className="sg-actions">
          <button type="button" className="sg-ghost" disabled={!canUndo} onClick={undo}>되돌리기</button>
          <button type="button" className="sg-ghost" onClick={onCancel}>{cancelLabel}</button>
          <button type="button" className="sg-confirm" disabled={empty} onClick={() => onDone(ed.current.mask)}>{doneLabel}</button>
        </div>
      </div>
    </div>
  );
}
