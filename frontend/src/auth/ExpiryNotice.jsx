/* 로그인 만료 안내 창 (docs/login_extend.md 3장).
   만료 30분 전, 10분 전에 연장할지 묻고, 만료 시각이 되면 onExpire로 로그아웃시킨다.
   연장하면 만료 시각이 바뀌어 안내 기록도 처음부터 다시 센다 (30분 전에 연장하면 10분 전 안내는 새 만료 시각 기준). */
import { useEffect, useRef, useState } from 'react';

const NOTICE_MIN = [30, 10]; // 안내 시점: 만료 몇 분 전

export default function ExpiryNotice({ expiresAt, onExtend, onExpire }) {
  const [notice, setNotice] = useState(null); // 안내 창에 보일 남은 분, 닫혀 있으면 null
  const [busy, setBusy] = useState(false);
  const shown = useRef(new Set()); // 이 만료 시각에 이미 안내한 시점

  useEffect(() => {
    shown.current = new Set();
    setNotice(null);
    if (!expiresAt) return undefined;
    const check = () => {
      const left = expiresAt.getTime() - Date.now();
      if (left <= 0) {
        clearInterval(timer);
        setNotice(null);
        onExpire();
        return;
      }
      // 화면을 늦게 연 경우처럼 여러 시점을 한꺼번에 지났으면 가장 가까운 시점 한 번만 안내
      const due = NOTICE_MIN.filter((m) => left <= m * 60000 && !shown.current.has(m));
      if (!due.length) return;
      const at = Math.min(...due);
      NOTICE_MIN.forEach((m) => { if (m >= at) shown.current.add(m); });
      setNotice(Math.ceil(left / 60000));
    };
    const timer = setInterval(check, 1000);
    check();
    return () => clearInterval(timer);
  }, [expiresAt, onExpire]);

  useEffect(() => {
    if (!notice) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setNotice(null); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [notice]);

  if (!notice) return null;

  const extend = async () => {
    if (busy) return;
    setBusy(true);
    await onExtend();
    setBusy(false);
    setNotice(null);
  };

  return (
    // 아니요를 누르거나 답하지 않으면 다음 시점에 다시 묻고, 마지막 안내 뒤에는 만료 시각에 로그아웃
    <div className="auth-modal open">
      <div className="auth-modal-box" role="alertdialog" aria-modal="true" aria-labelledby="expiry-title" aria-describedby="expiry-desc">
        <h2 className="auth-modal-title" id="expiry-title">로그인 시간 연장</h2>
        <p className="auth-modal-sub" id="expiry-desc">{notice}분 후 자동 로그아웃됩니다. 로그인 시간을 연장하시겠습니까?</p>
        <div className="auth-choice">
          <button type="button" className="auth-choice-no" onClick={() => setNotice(null)}>아니요</button>
          <button type="button" className="auth-submit" disabled={busy} onClick={extend}>연장</button>
        </div>
      </div>
    </div>
  );
}
