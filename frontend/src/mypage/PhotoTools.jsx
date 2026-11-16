/* 사진첩 카드의 ⋯ 메뉴(크게 보기, 다운로드, 삭제), 크게 보기 창, 삭제 확인 창. 다운로드는 utils/download.js */
import { useEffect, useRef, useState } from 'react';
import { formatKoreanDate } from '../utils/date.js';

export function PhotoMenu({ item, onView, onDownload, onDelete }) {
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
          <button type="button" role="menuitem" className="danger" onClick={pick(onDelete)}>삭제</button>
        </div>
      )}
    </div>
  );
}

export function PhotoViewer({ item, onClose, onDownload, onDelete }) {
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
            <button type="button" className="as-btn ghost danger" onClick={() => onDelete(item)}>삭제</button>
            <button type="button" className="as-btn ghost" onClick={onClose}>닫기</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// 삭제 확인 창. 삭제는 되돌릴 수 없어 한 번 더 확인한다. busy 동안 버튼을 막아 두 번 요청하지 않게
export function DeleteConfirm({ item, busy, onCancel, onConfirm }) {
  useEffect(() => {
    const esc = (e) => { if (e.key === 'Escape' && !busy) onCancel(); };
    document.addEventListener('keydown', esc);
    return () => document.removeEventListener('keydown', esc);
  }, [busy, onCancel]);

  return (
    <div className="as-viewer as-confirm" role="alertdialog" aria-modal="true" aria-label="사진 삭제 확인" onClick={busy ? undefined : onCancel}>
      <div className="as-confirm-box" onClick={(e) => e.stopPropagation()}>
        <img src={item.thumb_url} alt="" />
        <p className="as-confirm-title">사진을 삭제합니다.</p>
        <p className="as-confirm-desc">삭제한 사진은 사진첩과 내 작업 기록에서 모두 사라지며 복구할 수 없습니다.</p>
        <div className="as-confirm-foot">
          <button type="button" className="as-btn ghost" disabled={busy} onClick={onCancel}>취소</button>
          <button type="button" className="as-btn danger" disabled={busy} onClick={() => onConfirm(item)}>{busy ? '삭제 중입니다' : '삭제'}</button>
        </div>
      </div>
    </div>
  );
}
