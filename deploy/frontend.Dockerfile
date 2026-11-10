# MOA 화면 이미지. 두 단계 빌드
# 1단계 Node.js에서 화면 빌드, 2단계 nginx에 빌드 결과만 복사. 최종 이미지에 Node.js·소스 미포함
# 빌드: deploy 폴더에서 docker compose build, 또는 저장소 최상위 폴더에서
#   docker build -f deploy/frontend.Dockerfile -t moa-frontend:1 .

# 1단계: 개발 PC와 같은 Node.js 24
FROM node:24-alpine AS build
WORKDIR /src

# 패키지 목록만 먼저 복사해 설치. 화면 코드 수정 시 이 층 재사용
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# 화면이 모든 요청을 실제 서버 /api로 보내도록 real 모드로 빌드. 개발용 .env 파일은 빌드 자료에서 제외
ENV VITE_API_MODE=real
RUN npm run build

# 2단계: 정적 파일 제공과 /api 전달
FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
