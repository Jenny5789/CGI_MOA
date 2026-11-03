# 화면 (React + Vite) 빌드 후 nginx로 제공 (docker-compose.yml 의 web 서비스)
# build context 는 프로젝트 맨 위 폴더, 보내는 것은 web.Dockerfile.dockerignore 가 정함

FROM node:24-slim AS build
WORKDIR /app
# 패키지 목록을 코드보다 먼저 복사: 코드만 고쳤을 때 npm ci 를 다시 하지 않도록
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# API 모드는 빌드할 때 굳는다 (mock 가짜 서버 / mixed 실제+가짜 / real 전부 실제)
# 지정하지 않으면 화면이 mock 으로 만들어지므로 기본값을 mixed 로 둔다
ARG VITE_API_MODE=mixed
ENV VITE_API_MODE=$VITE_API_MODE
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
