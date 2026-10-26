import { getToken, request, setToken } from './client.js';

// 로그인 만료 시각 (서버가 준 expires_at, 한국 시간 글자). 연장 안내 창의 타이머 기준 → docs/login_extend.md
export const EXPIRES_KEY = 'moa_token_expires';
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

// 명세 2-2. 가입하면 바로 로그인 상태가 된다 (토큰 저장). form: { username, password, email, phone? }
export async function register(form) {
  const data = await request('POST', '/auth/register', form);
  setToken(data.token);
  setExpiresAt(data.expires_at);
  return data.user;
}

// 명세 2-6. 아이디 중복확인 → { username, available }
export function checkUsername(username) {
  return request('GET', `/auth/check-username?username=${encodeURIComponent(username)}`);
}

// 저장된 토큰이 아직 유효한지 서버에 확인 (명세 2-3, 화면을 열 때 1회, 10/18)
// 만료·무효(401)면 토큰을 지우고 false. 서버에 닿지 못하는 등 다른 실패는 확인할 수 없으니 그대로 둔다(true)
export async function checkLogin() {
  if (!getToken()) return false;
  try {
    await request('GET', '/me', undefined, { notifyExpired: false });
    return true;
  } catch (e) {
    if (e.status !== 401) return true;
    setToken(null);
    return false;
  }
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
