import { getToken, request, setToken } from './client.js';

// 명세 2-1. 성공하면 토큰을 저장하고 사용자 정보를 돌려준다. 실패하면 ApiError를 던진다
export async function login(username, password) {
  const data = await request('POST', '/auth/login', { username, password });
  setToken(data.token);
  return data.user;
}

// 명세 8-6. 토큰을 바로 지우고 서버에도 알린다. 서버 요청이 실패해도 화면에서는 로그아웃된다
export async function logout() {
  const token = getToken();
  setToken(null);
  if (!token) return;
  try {
    await request('POST', '/auth/logout', undefined, { notifyExpired: false, token });
  } catch { /* 이미 만료됐거나 서버가 꺼져 있어도 무시 */ }
}
