/* 합성 기본 설정 (마이페이지 설정 → 합성 기본 설정).
   합성하기 화면의 합성 설정 팝업이 처음 열릴 때 체크해 둘 값. 알림 설정처럼 이 브라우저에 저장한다.
   refine: 상의 경계 보정. 영역 모양 유지는 11/11 UI에서 빼서, 예전에 저장한 값이 있어도 읽지 않는다 */
const KEY = 'moa_compose_defaults';
const OFF = { refine: false };

export function readComposeDefaults() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || 'null');
    return v ? { refine: !!v.refine } : { ...OFF };
  } catch {
    return { ...OFF };
  }
}

export function saveComposeDefaults(v) {
  try { localStorage.setItem(KEY, JSON.stringify({ refine: !!v.refine })); } catch { /* 저장 불가 시 이번만 */ }
}
