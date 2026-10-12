# MOA 웹 화면 (React)

`web/`의 HTML 시안을 React로 옮긴 것입니다. 화면 모양과 동작은 시안과 같습니다.

## 실행

Node.js가 필요합니다(확인한 버전: Node 24, npm 11).

```
cd frontend
npm install
npm run dev
```

터미널에 나오는 주소(기본 http://localhost:5173)로 접속합니다. 5173번이 이미 쓰이고 있으면 `npm run dev -- --port 5180`처럼 다른 번호를 줍니다.

## 화면 주소

- `/` 홈
- `/studio` 합성하기 (로그인해야 들어갈 수 있음)
- `/mypage` 마이페이지(사진첩)

## 파일

- `src/pages/Home.jsx`, `Studio.jsx`, `MyPage.jsx`: 세 화면
- `src/components/TopNav.jsx`: 위쪽 메뉴. 로그인 전에 합성하기를 누르면 로그인 팝업을 띄운다.
- `src/auth/AuthContext.jsx`: 로그인 상태와 로그인 팝업
- `src/api/`: 서버 요청. 화면은 서버에 직접 요청하지 않고 여기 함수를 부른다.
  - `client.js`: 모든 요청이 거치는 곳. 로그인 토큰을 붙이고, 로그인이 풀리면(401) 화면에 알린다.
  - `mock.js`: 가짜 서버. 서버가 생기기 전까지 대신 대답한다.
  - `auth.js`: 로그인, 로그아웃
  - `results.js`: 결과 목록, 저장/좋아요 (사진첩)
  - `me.js`: 내 정보 (마이페이지 프로필)
- `src/studio/canvas.js`: 합성하기 화면의 그리기 도우미
- `src/styles/`: 시안의 CSS를 그대로 가져옴. 페이지마다 그 페이지 CSS만 켜진다(`src/components/usePageStyle.js`). 세 페이지 CSS가 body와 공통 색상 값을 서로 다르게 정해서 한꺼번에 켜면 화면이 깨지기 때문이다.
- `public/assets/`: 이미지. 갤러리 이미지는 모두 AI로 만든 예시 이미지다.

## 가짜 서버와 실제 서버

서버가 아직 없어서 기본은 가짜 서버(`src/api/mock.js`)가 대답한다. 주소와 데이터 모양은 팀 API 명세 초안(2026-10-12)을 따른다. 명세가 바뀌면 `src/api/`와 `mock.js`를 함께 고친다.

실제 서버에 붙일 때는 `.env.example`을 `.env.local`로 복사해 `VITE_USE_MOCK=false`로 바꾸고 `VITE_API_TARGET`에 서버 주소를 적는다. 화면은 `/api/...`로 요청하고, 개발 서버(`vite.config.js`)가 주소 그대로 그 서버로 넘긴다. `.env.local`을 바꾼 뒤에는 `npm run dev`를 다시 켠다.

## 아직 흉내만 내는 부분 (서버 연결 때 바꿀 곳)

- 로그인: 요청 층(`src/api/auth.js`)으로 옮겼다. 지금은 가짜 서버가 대답해서 아이디 test / 비밀번호 test로만 로그인된다.
- 3단계 상의 추출: `Studio.jsx`의 `rebuildMask3`, `confirm3`. 찍은 점마다 동그라미로 잘라낼 뿐 SAM을 쓰지 않는다.
- 4단계 합성: `Studio.jsx`의 `compose`, `confirm4`. 3.2초 기다린 뒤 잘라낸 상의를 칠한 영역에 붙인다. AI 합성이 아니다.
- 사진첩(마이페이지): 요청 층(`src/api/results.js`)으로 옮겼다. 지금은 가짜 서버가 예시 이미지 26장으로 대답한다. 로그인하지 않으면 사진첩을 보여 주지 않는다.
- 내 작업 기록(합성하기 화면 오른쪽): `Studio.jsx`의 `SAMPLE_HISTORY`. 예시 이미지를 고정으로 넣어 두었다. → `listResults({ saved: true })`로 바꾸면 된다.
