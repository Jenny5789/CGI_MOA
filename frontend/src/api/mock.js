/* 가짜 서버. 실제 서버처럼 조금 기다린 뒤 { status, data } 를 돌려준다.
   기능을 하나씩 옮길 때마다 아래 routes에 주소를 추가한다. 주소 안의 {이름} 부분은 params로, ?뒤 조건은 query로 넘어온다.
   데이터는 메모리에만 있어서 새로고침하면 처음 상태로 돌아간다. */
const DEMO_ID = 'test';
const DEMO_PW = 'test';
const DEMO_TOKEN = 'mock-token';
const DELAY = 500;

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const ok = (data) => ({ status: 200, data });
const fail = (status, code, message) => ({ status, data: { error: { code, message } } });
// 로그인 유효 시간 (실제 서버 backend/auth.py TOKEN_HOURS와 같게). 가짜 서버는 만료를 실제로 확인하지는 않는다
const TOKEN_MS = 3 * 60 * 60 * 1000;
const expiresAt = () => new Date(Date.now() + TOKEN_MS).toISOString();

// 사진첩 예시 (예전 MyPage.jsx의 SAMPLE_ITEMS를 명세 5-3 모양으로 옮김). 사진은 public/assets/gallery의 예시 이미지
const SAMPLE_RESULTS = [
  ['SpringWarm_Female', '2026-10-09T11:20', false, false],
  ['SummerCool_Female', '2026-10-09T11:02', false, false],
  ['AutumnWarm_Male', '2026-10-08T20:45', false, false],
  ['MtFuji_Female', '2026-10-08T18:30', false, false],
  ['Paris_Female', '2026-10-08T15:12', false, false],
  ['girl_sitting', '2026-10-07T22:40', false, false],
  ['girl_Santorini', '2026-09-20T14:32', true, true],
  ['NewYork_Male', '2026-09-20T11:18', true, false],
  ['Paris_Female', '2026-09-19T21:03', true, true],
  ['BaseballCap_Male', '2026-09-18T16:27', true, false],
  ['girl_sitting', '2026-09-17T13:45', true, true],
  ['Watch_Female', '2026-09-16T09:12', true, false],
  ['girl_bag', '2026-09-15T18:20', true, false],
  ['Watch_Male', '2026-09-14T20:11', true, false],
  ['RooftopParty_Female', '2026-09-13T19:40', true, false],
  ['man_watch', '2026-09-12T15:05', true, true],
  ['girl_hat', '2026-09-11T12:30', true, false],
  ['Yacht_Female', '2026-09-10T17:55', true, false],
  ['man_car', '2026-09-08T10:22', true, false],
  ['Handbag_Female', '2026-09-07T21:48', true, true],
  ['Supercar_Male', '2026-09-05T14:10', true, false],
  ['LuxuryCar_Female', '2026-09-03T11:36', true, false],
  ['PrivateJet_Male', '2026-09-01T16:02', true, false],
  ['SpringWarm_Female', '2026-08-29T13:15', true, false],
  ['NewYork_Male', '2026-08-27T19:50', true, true],
  ['SummerCool_Female', '2026-08-25T10:08', true, false],
].map(([img, at, saved, favorite], i) => ({
  result_id: `res_${String(i + 1).padStart(3, '0')}`,
  image_url: `/assets/gallery/${img}.jpg`,
  thumb_url: `/assets/gallery/${img}.jpg`,
  created_at: `${at}:00+09:00`,
  saved,
  favorite,
  garment_image_id: null,
  person_image_id: null,
}));

const db = { results: SAMPLE_RESULTS };

const listItem = (r) => ({
  result_id: r.result_id, thumb_url: r.thumb_url, image_url: r.image_url, created_at: r.created_at, saved: r.saved, favorite: r.favorite,
});

const routes = {
  'POST /auth/login': (body) => {
    if (body && body.username === DEMO_ID && body.password === DEMO_PW) {
      return ok({ token: DEMO_TOKEN, expires_at: expiresAt(), user: { id: 1, username: DEMO_ID, name: 'MOA User' } });
    }
    return fail(401, 'INVALID_CREDENTIALS', '아이디 또는 비밀번호가 올바르지 않습니다');
  },
  'POST /auth/logout': () => ok({}),
  'POST /auth/extend': () => ok({ expires_at: expiresAt() }),

  'GET /me': () => ok({ id: 1, username: DEMO_ID, name: 'MOA User', email: 'moa.user@example.com', avatar_url: '/assets/gallery/girl_sitting.jpg' }),

  // 명세 6-1. created_at이 한국 시간(+09:00)으로 적혀 있어서 앞 10글자가 곧 한국 날짜다
  'GET /results': (body, params, query) => {
    let list = db.results;
    if (query.saved === 'true') list = list.filter((r) => r.saved);
    if (query.saved === 'false') list = list.filter((r) => !r.saved);
    if (query.favorite === 'true') list = list.filter((r) => r.favorite);
    if (query.date) list = list.filter((r) => r.created_at.slice(0, 10) === query.date);
    const dir = query.sort === 'old' ? 1 : -1;
    list = [...list].sort((a, b) => dir * a.created_at.localeCompare(b.created_at));
    const counts = {
      saved: db.results.filter((r) => r.saved).length,
      recent: db.results.filter((r) => !r.saved).length,
      favorite: db.results.filter((r) => r.favorite).length,
    };
    return ok({ items: list.map(listItem), counts, next_cursor: null });
  },

  'GET /results/{id}': (body, params) => {
    const r = db.results.find((x) => x.result_id === params.id);
    return r ? ok(r) : fail(404, 'NOT_FOUND', '결과를 찾을 수 없습니다');
  },

  'PATCH /results/{id}': (body, params) => {
    const r = db.results.find((x) => x.result_id === params.id);
    if (!r) return fail(404, 'NOT_FOUND', '결과를 찾을 수 없습니다');
    if (body && typeof body.saved === 'boolean') r.saved = body.saved;
    if (body && typeof body.favorite === 'boolean') r.favorite = body.favorite;
    return ok(r);
  },
};

// 로그인 없이 쓸 수 있는 주소
const PUBLIC = new Set(['POST /auth/login']);

// "GET /results/res_001?x=1" 을 routes의 "GET /results/{id}" 와 맞춰 본다
function match(method, path) {
  const [pathname, qs = ''] = path.split('?');
  const query = Object.fromEntries(new URLSearchParams(qs));
  const parts = pathname.split('/');
  for (const key of Object.keys(routes)) {
    const [m, pattern] = key.split(' ');
    if (m !== method) continue;
    const pp = pattern.split('/');
    if (pp.length !== parts.length) continue;
    const params = {};
    const hit = pp.every((seg, i) => {
      if (seg.startsWith('{') && seg.endsWith('}')) { params[seg.slice(1, -1)] = decodeURIComponent(parts[i]); return true; }
      return seg === parts[i];
    });
    if (hit) return { key, handler: routes[key], params, query };
  }
  return null;
}

export async function mockRequest(method, path, body, token) {
  await wait(DELAY);
  const found = match(method, path);
  const key = found ? found.key : `${method} ${path.split('?')[0]}`;
  if (!PUBLIC.has(key) && token !== DEMO_TOKEN) return fail(401, 'UNAUTHORIZED', '로그인이 필요합니다');
  if (!found) return fail(404, 'NOT_FOUND', `가짜 서버에 없는 주소입니다: ${key}`);
  // 실제 서버처럼 응답은 복사본을 준다 (화면이 받은 값을 고쳐도 가짜 서버 데이터는 그대로)
  const res = found.handler(body, found.params, found.query);
  return { status: res.status, data: JSON.parse(JSON.stringify(res.data)) };
}
