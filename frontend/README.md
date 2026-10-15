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
  - `mock.js`: 가짜 서버. 서버 없이 화면만 볼 때 대신 대답한다.
  - `auth.js`: 로그인, 로그아웃, 로그인 시간 연장(만료 시각)
  - `studio.js`: 사진 올리기, 상의 추출, 합성 요청·진행 확인·결과 (합성하기 화면)
  - `results.js`: 결과 목록, 저장/좋아요 (사진첩)
  - `me.js`: 내 정보 (마이페이지 프로필)
- `src/studio/canvas.js`: 합성하기 화면의 그리기 도우미
- `src/styles/`: 시안의 CSS를 그대로 가져옴. 페이지마다 그 페이지 CSS만 켜진다(`src/components/usePageStyle.js`). 세 페이지 CSS가 body와 공통 색상 값을 서로 다르게 정해서 한꺼번에 켜면 화면이 깨지기 때문이다.
- `public/assets/`: 이미지. 갤러리 이미지는 모두 AI로 만든 예시 이미지다.

## 가짜 서버와 실제 서버

주소와 데이터 모양은 팀 API 명세(`docs/api.md`)를 따른다. 명세가 바뀌면 `src/api/`와 `mock.js`를 함께 고친다.

어느 서버를 쓸지는 `.env.local`의 `VITE_API_MODE`로 고른다 (`.env.example`을 복사해서 만든다).

| 값 | 쓰는 서버 | 로그인 |
|---|---|---|
| `mock` (기본) | 모두 가짜 서버. 서버 없이 화면만 볼 때 | `test` / `test` |
| `mixed` | 실제 서버에 있는 기능은 실제 서버로 (지금은 전부) | `test` / `test1234` |
| `real` | 모두 실제 서버 | `test` / `test1234` |

화면은 `/api/...`로 요청하고, 개발 서버(`vite.config.js`)가 `VITE_API_TARGET`(기본 `http://localhost:8000`)으로 넘긴다. `.env.local`을 바꾼 뒤에는 `npm run dev`를 다시 켠다. 서버 실행 방법은 맨 위 `README.md`.

## 아직 서버에 안 가는 것

- 3단계 다듬기 팝업에서 고친 상의 윤곽: 서버는 SAM2가 찾은 윤곽으로 합성한다 (반영 방법은 팀 합의 필요)
- 합성 설정의 체크 두 개(`opts.refine`, `opts.shape`): 서버가 아직 쓰지 않아 보내지 않는다
- 회원가입: 서버는 준비됨(`POST /api/auth/register`), 화면은 "준비 중" 알림
