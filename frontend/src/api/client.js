/* 서버 요청은 모두 여기를 거친다.
   주소와 데이터 모양은 팀 API 명세 초안(2026-10-12)을 따른다. 명세의 주소는 모두 /api로 시작하고, 여기 path에는 /api 뒤만 적는다.

   어느 서버에 보낼지 (.env.local의 VITE_API_MODE)
   - mock  (기본): 모두 가짜 서버(mock.js)가 대답
   - mixed       : 실제 서버(backend/)에 있는 기능만 실제 서버로, 나머지는 가짜 서버로
                   실제 서버에 있는 것: 사진 올리기, 상의 추출, 합성 요청·진행 확인·결과 받기 (REAL_ROUTES)
                   아직 없는 것(서버 담당 몫): 로그인, 내 정보, 사진첩 목록·저장/좋아요 → 가짜 서버
   - real        : 모두 실제 서버로
   예전 설정 VITE_USE_MOCK=false 는 real 과 같다. */
import { mockRequest } from './mock.js';

const env = import.meta.env;
export const API_MODE = env.VITE_API_MODE || (env.VITE_USE_MOCK === 'false' ? 'real' : 'mock');
export const USE_MOCK = API_MODE === 'mock';
const BASE = '/api'; // 개발 중에는 vite.config.js의 프록시가 실제 서버로 넘긴다

// mixed 모드에서 실제 서버로 보낼 요청 ("방식 주소" 모양으로 검사)
const REAL_ROUTES = [
  /^POST \/images$/,
  /^POST \/extract$/,
  /^POST \/compose$/,
  /^GET \/jobs\/[^/?]+$/,
  /^GET \/results\/[^/?]+$/, // 결과 하나 받기(5-3). 목록(6-1)과 저장/좋아요(6-2)는 아직 가짜 서버
];

const goesToRealServer = (method, path) => {
  if (API_MODE === 'real') return true;
  if (API_MODE === 'mock') return false;
  const key = `${method} ${path}`;
  return REAL_ROUTES.some((re) => re.test(key));
};

const TOKEN_KEY = 'moa_token';
export const UNAUTHORIZED_EVENT = 'moa:unauthorized';

export const getToken = () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
export const setToken = (token) => {
  try { if (token) localStorage.setItem(TOKEN_KEY, token); else localStorage.removeItem(TOKEN_KEY); } catch { /* 저장 불가 시 무시 */ }
};

// 서버가 실패를 돌려줬을 때. 명세의 오류 형식 { error: { code, message } } 를 담는다. status 0은 서버에 아예 닿지 못한 경우
export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// body: JSON으로 보낼 값, 또는 사진 같은 파일을 보낼 때는 FormData
// notifyExpired: 401일 때 화면에 로그인 만료를 알릴지. 로그아웃 요청처럼 알릴 필요가 없으면 false
// token: 저장된 토큰 대신 쓸 토큰 (로그아웃처럼 토큰을 먼저 지운 뒤 보낼 때)
export async function request(method, path, body, { notifyExpired = true, token = getToken() } = {}) {
  let res;
  if (!goesToRealServer(method, path)) {
    res = await mockRequest(method, path, body, token);
  } else {
    const headers = {};
    const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
    if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json'; // FormData는 브라우저가 알아서 정함
    if (token) headers.Authorization = `Bearer ${token}`;
    let r;
    try {
      r = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : (isForm ? body : JSON.stringify(body)) });
    } catch {
      throw new ApiError(0, 'NETWORK_ERROR', '서버에 연결할 수 없습니다');
    }
    const data = await r.json().catch(() => null);
    res = { status: r.status, data };
  }

  if (res.status >= 200 && res.status < 300) return res.data;
  // 로그인이 풀렸으면 토큰을 지우고 화면(AuthContext)에 알린다. 로그인 요청 자체의 실패는 제외
  if (res.status === 401 && token && notifyExpired) {
    setToken(null);
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  const err = (res.data && res.data.error) || {};
  throw new ApiError(res.status, err.code || 'UNKNOWN', err.message || '요청을 처리하지 못했습니다');
}
