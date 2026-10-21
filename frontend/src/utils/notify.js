/* 합성 완료 알림 (마이페이지 설정 → 알림 설정).
   브라우저 알림 허용은 기기마다 따로라서, 켜고 끈 값도 서버가 아니라 이 브라우저에 저장한다.
   합성하기 화면은 합성이 끝났을 때 다른 탭을 보고 있으면 알림을 띄운다. */
const KEY = 'moa_notify_compose';

export const notifySupported = () => typeof window !== 'undefined' && 'Notification' in window;

export function notifyEnabled() {
  try { return localStorage.getItem(KEY) === '1' && notifySupported() && Notification.permission === 'granted'; } catch { return false; }
}

// 켜기: 브라우저에 알림 허용을 물어보고, 허용했을 때만 켠다. 결과 'on' / 'denied' / 'unsupported'
export async function enableNotify() {
  if (!notifySupported()) return 'unsupported';
  const perm = Notification.permission === 'default' ? await Notification.requestPermission() : Notification.permission;
  if (perm !== 'granted') return 'denied';
  try { localStorage.setItem(KEY, '1'); } catch { /* 저장 불가 시 이번만 */ }
  return 'on';
}

export function disableNotify() {
  try { localStorage.removeItem(KEY); } catch { /* 무시 */ }
}

export function notifyComposeDone() {
  if (!notifyEnabled() || !document.hidden) return; // 화면을 보고 있으면 결과가 바로 보이므로 띄우지 않는다
  const n = new Notification('MOA 합성 완료', { body: '상의 착용 이미지가 완성되었습니다.', tag: 'moa-compose' });
  n.onclick = () => { window.focus(); n.close(); };
}
