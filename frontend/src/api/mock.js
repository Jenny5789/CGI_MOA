/* 가짜 서버. 실제 서버처럼 조금 기다린 뒤 { status, data } 를 돌려준다.
   기능을 하나씩 옮길 때마다 아래 routes에 주소를 추가한다. 주소 안의 {이름} 부분은 params로, ?뒤 조건은 query로 넘어온다.
   데이터는 메모리에만 있어서 새로고침하면 처음 상태로 돌아간다. */
import { normalizeEmail, normalizePhone, passwordOk, usernameOk } from '../auth/signupRules.js';

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

// images, extractions, jobs: 합성하기에서 올린 사진·추출·합성 작업. 사진은 브라우저 안 주소(blob:)로만 들고 있는다
const db = { results: SAMPLE_RESULTS, images: {}, extractions: {}, jobs: {}, recent: [] }; // recent: 직접 올린 사진 (최근 사용한 사진)

const listItem = (r) => ({
  result_id: r.result_id, thumb_url: r.thumb_url, image_url: r.image_url, created_at: r.created_at, saved: r.saved, favorite: r.favorite,
});

let seq = 0;
const newId = (prefix) => `${prefix}_mock${String(++seq).padStart(8, '0')}`; // 명세처럼 접두어 + 12자리
// 지금 한국 시간 글자 (예: 2026-10-16T14:05:00+09:00). 사진첩 예시의 created_at과 같은 모양
const nowKst = () => `${new Date(Date.now() + 9 * 60 * 60 * 1000).toISOString().slice(0, 19)}+09:00`;
const COMPOSE_MS = 6000; // 가짜 합성에 걸리는 시간. 화면은 2초마다 진행을 묻는다

// 가짜 추출 윤곽: 포함 점(또는 box)을 감싸는 타원을 흰색으로 칠한 흑백 PNG. 긴 변 1024px 이하로 만든다 (화면이 사진 크기에 맞춰 늘림)
async function fakeMask(image, points, box) {
  let x1; let y1; let x2; let y2;
  if (box) ({ x1, y1, x2, y2 } = box);
  else {
    const pos = points.filter((p) => p.label === 1);
    x1 = Math.min(...pos.map((p) => p.x)); x2 = Math.max(...pos.map((p) => p.x));
    y1 = Math.min(...pos.map((p) => p.y)); y2 = Math.max(...pos.map((p) => p.y));
  }
  const cx = (x1 + x2) / 2;
  const cy = (y1 + y2) / 2;
  const rx = Math.max((x2 - x1) / 2 + 0.1, 0.15);
  const ry = Math.max((y2 - y1) / 2 + 0.1, 0.15);

  const s = Math.min(1, 1024 / Math.max(image.width, image.height));
  const c = document.createElement('canvas');
  c.width = Math.round(image.width * s);
  c.height = Math.round(image.height * s);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.fillStyle = '#fff';
  ctx.beginPath();
  ctx.ellipse(cx * c.width, cy * c.height, rx * c.width, ry * c.height, 0, 0, Math.PI * 2);
  ctx.fill();
  const blob = await new Promise((r) => c.toBlob(r, 'image/png'));

  const clamp = (v) => Math.min(Math.max(v, 0), 1);
  const [bx1, by1, bx2, by2] = [clamp(cx - rx), clamp(cy - ry), clamp(cx + rx), clamp(cy + ry)];
  return {
    url: URL.createObjectURL(blob),
    bbox: { // 원본 픽셀 기준 (명세 4-1)
      x: Math.round(bx1 * image.width), y: Math.round(by1 * image.height),
      w: Math.round((bx2 - bx1) * image.width), h: Math.round((by2 - by1) * image.height),
    },
  };
}

// 회원 (회원가입한 사람은 새로고침 전까지만 남는다). 가짜 서버는 토큰 하나(DEMO_TOKEN)를 모두에게 준다
const users = [{ id: 1, username: DEMO_ID, password: DEMO_PW, name: 'MOA User', email: 'moa.user@example.com' }];

const routes = {
  'POST /auth/login': (body) => {
    const u = body && users.find((x) => x.username === body.username && x.password === body.password);
    if (u) {
      return ok({ token: DEMO_TOKEN, expires_at: expiresAt(), user: { id: u.id, username: u.username, name: u.name } });
    }
    return fail(401, 'INVALID_CREDENTIALS', '아이디 또는 비밀번호가 올바르지 않습니다');
  },
  // 명세 2-2, 2-6. 실제 서버(backend/routers/auth.py)와 같은 규칙과 오류 코드
  'POST /auth/register': (body) => {
    const username = ((body && body.username) || '').trim();
    if (!usernameOk(username)) return fail(400, 'INVALID_USERNAME', '아이디는 공백 없이 12자 이하로 입력해 주세요.');
    if (!passwordOk(body.password)) return fail(400, 'INVALID_PASSWORD', '비밀번호는 8자 이상이고 숫자를 포함해야 합니다.');
    const email = normalizeEmail(body.email);
    if (!email) return fail(400, 'INVALID_EMAIL', '올바른 이메일 주소를 입력해 주세요.');
    const phone = (body.phone || '').trim() ? normalizePhone(body.phone) : null;
    if (phone === null && (body.phone || '').trim()) return fail(400, 'INVALID_PHONE', '휴대폰 번호를 010-1234-5678 형식으로 입력해 주세요.');
    if (users.some((u) => u.username === username)) return fail(409, 'DUPLICATE_USERNAME', '이미 사용 중인 아이디입니다.');
    if (users.some((u) => u.email === email)) return fail(409, 'DUPLICATE_EMAIL', '이미 가입된 이메일입니다.');
    const u = { id: users.length + 1, username, password: body.password, name: username, email, phone };
    users.push(u);
    return ok({ token: DEMO_TOKEN, expires_at: expiresAt(), user: { id: u.id, username, name: u.name } });
  },
  'GET /auth/check-username': (body, params, query) => {
    const username = (query.username || '').trim();
    if (!usernameOk(username)) return fail(400, 'INVALID_USERNAME', '아이디는 공백 없이 12자 이하로 입력해 주세요.');
    return ok({ username, available: !users.some((u) => u.username === username) });
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
      favorite: db.results.filter((r) => r.saved && r.favorite).length,
    };
    return ok({ items: list.map(listItem), counts, next_cursor: null });
  },

  'GET /results/{id}': (body, params) => {
    const r = db.results.find((x) => x.result_id === params.id);
    return r ? ok(r) : fail(404, 'NOT_FOUND', '결과를 찾을 수 없습니다');
  },

  // 예시 결과에는 재료가 없어서 404 (화면은 결과만 보여 준다)
  'GET /results/{id}/source': (body, params) => {
    const r = db.results.find((x) => x.result_id === params.id);
    if (!r) return fail(404, 'RESULT_NOT_FOUND', '결과를 찾을 수 없습니다.');
    return r.source ? ok({ result_id: r.result_id, ...r.source }) : fail(404, 'SOURCE_NOT_FOUND', '이 결과의 재료를 찾을 수 없습니다.');
  },

  'PATCH /results/{id}': (body, params) => {
    const r = db.results.find((x) => x.result_id === params.id);
    if (!r) return fail(404, 'NOT_FOUND', '결과를 찾을 수 없습니다');
    if (body && typeof body.saved === 'boolean') r.saved = body.saved;
    if (body && typeof body.favorite === 'boolean') r.favorite = body.favorite;
    return ok(r);
  },

  // 명세 3-1. body는 FormData (file, kind)
  'POST /images': async (body) => {
    const kind = body.get('kind');
    if (kind !== 'garment' && kind !== 'person') return fail(400, 'INVALID_KIND', 'kind는 garment 또는 person이어야 합니다.');
    const file = body.get('file');
    let bmp;
    try { bmp = await createImageBitmap(file); } catch { return fail(400, 'INVALID_IMAGE', '이미지를 읽을 수 없습니다.'); }
    const image = { image_id: newId('img'), url: URL.createObjectURL(file), width: bmp.width, height: bmp.height };
    bmp.close();
    db.images[image.image_id] = image;
    if (body.get('from_sample') !== '1') {
      db.recent.unshift({ ...image, kind, thumb_url: image.url, created_at: new Date().toISOString() });
    }
    return ok(image);
  },

  // 명세 3-2. 가짜 서버는 같은 파일 묶기·24시간 정리는 하지 않는다 (새로고침하면 비워짐)
  'GET /images/recent': (body, params, query) => {
    if (query.kind !== 'garment' && query.kind !== 'person') return fail(400, 'INVALID_KIND', 'kind는 garment 또는 person이어야 합니다.');
    return ok({ items: db.recent.filter((r) => r.kind === query.kind).slice(0, 12) });
  },

  // 명세 4-1. SAM2 대신 찍은 점을 감싸는 타원을 상의 영역으로 돌려준다. cutout_url은 화면이 쓰지 않아 원본 사진 주소를 넣는다
  'POST /extract': async (body) => {
    const points = body.points || [];
    if (!body.box && !points.some((p) => p.label === 1)) {
      return fail(400, 'NO_POSITIVE_POINT', '상의 위에 포함 점(왼쪽 클릭)을 찍거나 상의를 감싸는 박스를 그려 주세요.');
    }
    const image = db.images[body.image_id];
    if (!image) return fail(404, 'IMAGE_NOT_FOUND', '사진을 찾을 수 없습니다. 다시 올려 주세요.');
    const mask = await fakeMask(image, points, body.box);
    const ext = { extraction_id: newId('ext'), mask_url: mask.url, cutout_url: image.url, bbox: mask.bbox };
    db.extractions[ext.extraction_id] = { ...ext, image_id: image.image_id };
    return ok(ext);
  },

  // 명세 5-1. body는 FormData (extraction_id, person_image_id, area_mask). 실제 합성은 하지 않는다
  'POST /compose': (body) => {
    const ext = db.extractions[body.get('extraction_id')];
    if (!ext) return fail(404, 'EXTRACTION_NOT_FOUND', '추출 결과를 찾을 수 없습니다. 다시 추출해 주세요.');
    const person = db.images[body.get('person_image_id')];
    if (!person) return fail(404, 'IMAGE_NOT_FOUND', '사진을 찾을 수 없습니다. 다시 올려 주세요.');
    const garmentMask = body.get('garment_mask');
    const source = { // 작업 기록에서 1~4단계를 채울 재료 (GET /results/{id}/source)
      garment: db.images[ext.image_id], person, extraction_id: ext.extraction_id,
      garment_mask_url: garmentMask ? URL.createObjectURL(garmentMask) : ext.mask_url,
      area_mask_url: URL.createObjectURL(body.get('area_mask')),
      refine: body.get('refine') === '1', shape_control: body.get('shape_control') === '1',
    };
    const job = { job_id: newId('job'), start: Date.now(), garment_image_id: ext.image_id, person, source, result_id: null };
    db.jobs[job.job_id] = job;
    return ok({ job_id: job.job_id, status: 'queued', queue_position: 1 });
  },

  // 명세 5-2. 요청 뒤 지난 시간으로 진행률을 만든다. COMPOSE_MS가 지나면 인물 사진을 그대로 결과로 만들어 "최근 작업"(saved: false)에 넣는다
  'GET /jobs/{id}': (body, params) => {
    const job = db.jobs[params.id];
    if (!job) return fail(404, 'JOB_NOT_FOUND', '작업을 찾을 수 없습니다.');
    const progress = Math.min((Date.now() - job.start) / COMPOSE_MS, 1);
    if (progress >= 1 && !job.result_id) {
      const r = {
        result_id: newId('res'), image_url: job.person.url, thumb_url: job.person.url, created_at: nowKst(), saved: false, favorite: false,
        garment_image_id: job.garment_image_id, person_image_id: job.person.image_id, source: job.source,
      };
      db.results.unshift(r);
      job.result_id = r.result_id;
    }
    return ok({
      job_id: job.job_id, status: job.result_id ? 'done' : 'running', progress, queue_position: 0, result_id: job.result_id, error: null,
    });
  },
};

// 로그인 없이 쓸 수 있는 주소
const PUBLIC = new Set(['POST /auth/login', 'POST /auth/register', 'GET /auth/check-username']);

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
  const res = await found.handler(body, found.params, found.query); // 사진을 읽는 주소는 기다려야 해서 await
  return { status: res.status, data: JSON.parse(JSON.stringify(res.data)) };
}
