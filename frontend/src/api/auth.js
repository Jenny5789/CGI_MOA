import { getToken, request, setToken } from './client.js';

// 로그인 만료 시각 (서버가 준 expires_at, 한국 시간 글자). 연장 안내 창의 타이머 기준 → docs/login_extend.md
const EXPIRES_KEY = 'moa_token_expires';
export const getExpiresAt = () => {
  try { const v = localStorage.getItem(EXPIRES_KEY); return v ? new Date(v) : null; } catch { return null; }
};
const setExpiresAt = (v) => {
  try { if (v) localStorage.setItem(EXPIRES_KEY, v); else localStorage.removeItem(EXPIRES_KEY); } catch { /* 저장 불가 시 무시 */ }
};

// 명세 2-1. 성공하면 토큰을 저장하고 사용자 정보를 돌려준다. 실패하면 ApiError를 던진다
export async function login(username, password) {
  const data = await request('POST', '/auth/login', { username, password });
  setToken(data.token);
  setExpiresAt(data.expires_at);
  return data.user;
}

// 로그인 시간 연장 (명세 외 추가 10/15). 성공하면 새 만료 시각(Date)을 돌려준다. 이미 만료됐으면 401 → 로그아웃 처리됨
export async function extendLogin() {
  const data = await request('POST', '/auth/extend');
  setExpiresAt(data.expires_at);
  return new Date(data.expires_at);
}

// 명세 8-6. 토큰을 바로 지우고 서버에도 알린다. 서버 요청이 실패해도 화면에서는 로그아웃된다
export async function logout() {
  const token = getToken();
  setToken(null);
  setExpiresAt(null);
  if (!token) return;
  try {
    await request('POST', '/auth/logout', undefined, { notifyExpired: false, token });
  } catch { /* 이미 만료됐거나 서버가 꺼져 있어도 무시 */ }
}
