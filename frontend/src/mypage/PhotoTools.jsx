/* 사진첩 카드의 ⋯ 메뉴(크게 보기, 다운로드)와 크게 보기 창. 다운로드는 utils/download.js */
import { useEffect, useRef, useState } from 'react';
import { formatKoreanDate } from '../utils/date.js';

export function PhotoMenu({ item, onView, onDownload }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const esc = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);

  const pick = (fn) => () => { setOpen(false); fn(item); };

  return (
    <div className="as-more" ref={ref}>
      <button type="button" className="as-more-btn" aria-label="사진 메뉴" aria-expanded={open} onClick={() => setOpen((o) => !o)}>⋯</button>
      {open && (
        <div className="as-more-menu" role="menu">
          <button type="button" role="menuitem" onClick={pick(onView)}>크게 보기</button>
          <button type="button" role="menuitem" onClick={pick(onDownload)}>다운로드</button>
        </div>
      )}
    </div>
  );
}

export function PhotoViewer({ item, onClose, onDownload }) {
  useEffect(() => {
    const esc = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', esc);
    return () => document.removeEventListener('keydown', esc);
  }, [onClose]);

  return (
    <div className="as-viewer" role="dialog" aria-modal="true" aria-label="결과 크게 보기" onClick={onClose}>
      <div className="as-viewer-box" onClick={(e) => e.stopPropagation()}>
        <img src={item.image_url} alt="합성 결과" />
        <div className="as-viewer-foot">
          <span>{formatKoreanDate(item.created_at)}</span>
          <div>
            <button type="button" className="as-btn" onClick={() => onDownload(item)}>다운로드</button>
            <button type="button" className="as-btn ghost" onClick={onClose}>닫기</button>
          </div>
        </div>
      </div>
    </div>
  );
}
