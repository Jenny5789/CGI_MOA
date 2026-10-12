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
- `src/studio/canvas.js`: 합성하기 화면의 그리기 도우미
- `src/styles/`: 시안의 CSS를 그대로 가져옴. 페이지마다 그 페이지 CSS만 켜진다(`src/components/usePageStyle.js`). 세 페이지 CSS가 body와 공통 색상 값을 서로 다르게 정해서 한꺼번에 켜면 화면이 깨지기 때문이다.
- `public/assets/`: 이미지. 갤러리 이미지는 모두 AI로 만든 예시 이미지다.

## 아직 흉내만 내는 부분 (서버 연결 때 바꿀 곳)

- 로그인: `AuthContext.jsx`의 `login()`. 지금은 아이디 test / 비밀번호 test로만 로그인되고 상태는 브라우저에만 저장된다. → 백엔드 `/auth/login`
- 3단계 상의 추출: `Studio.jsx`의 `rebuildMask3`, `confirm3`. 찍은 점마다 동그라미로 잘라낼 뿐 SAM을 쓰지 않는다. → `/extract`, `/extract/{번호}/select`, `/extract/{번호}/cutout`
- 4단계 합성: `Studio.jsx`의 `compose`, `confirm4`. 3.2초 기다린 뒤 잘라낸 상의를 칠한 영역에 붙인다. AI 합성이 아니다. → `/composite`로 작업 번호를 받고, `/job/{번호}`로 끝났는지 확인한 뒤 `/result/{번호}`로 결과를 받는다.
- 내 작업 기록, 사진첩: `Studio.jsx`의 `SAMPLE_HISTORY`, `MyPage.jsx`의 `SAMPLE_ITEMS`. 예시 이미지를 고정으로 넣어 두었다. → `/history`

## 백엔드 (참고)

FastAPI 백엔드는 아직 이 저장소에 없습니다(서지섭 PC의 이전 CGI 프로젝트에 있음). 백엔드의 `/composite`는 지금 AnyDoor가 아니라 오려낸 객체를 붙이고 색감과 그림자만 맞추는 방식이라, 상의 합성에 쓰려면 AnyDoor로 바꿔야 합니다.
