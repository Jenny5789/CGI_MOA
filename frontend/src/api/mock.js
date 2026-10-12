/* 가짜 서버. 실제 서버처럼 조금 기다린 뒤 { status, data } 를 돌려준다.
   기능을 하나씩 옮길 때마다 아래 routes에 주소를 추가한다. */
const DEMO_ID = 'test';
const DEMO_PW = 'test';
const DEMO_TOKEN = 'mock-token';
const DELAY = 500;

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const ok = (data) => ({ status: 200, data });
const fail = (status, code, message) => ({ status, data: { error: { code, message } } });

const routes = {
  'POST /auth/login': (body) => {
    if (body && body.username === DEMO_ID && body.password === DEMO_PW) {
      return ok({ token: DEMO_TOKEN, user: { id: 1, username: DEMO_ID, name: 'MOA User' } });
    }
    return fail(401, 'INVALID_CREDENTIALS', '아이디 또는 비밀번호가 올바르지 않습니다');
  },
  'POST /auth/logout': () => ok({}),
};

// 로그인 없이 쓸 수 있는 주소
const PUBLIC = new Set(['POST /auth/login']);

export async function mockRequest(method, path, body, token) {
  await wait(DELAY);
  const key = `${method} ${path}`;
  if (!PUBLIC.has(key) && token !== DEMO_TOKEN) return fail(401, 'UNAUTHORIZED', '로그인이 필요합니다');
  const handler = routes[key];
  if (!handler) return fail(404, 'NOT_FOUND', `가짜 서버에 없는 주소입니다: ${key}`);
  return handler(body);
}
