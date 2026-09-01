FROM node:20-slim AS builder

WORKDIR /app

# Build args (configurados no docker-compose.yml)
# VITE_BASE_PATH: subpath do deploy (ex: "/otrs/" ou "/" para raiz)
# VITE_OTEL_ENDPOINT: URL do OTel Collector (vazio = desabilitado)
ARG VITE_BASE_PATH="/"
ARG VITE_OTEL_ENDPOINT=""
ENV VITE_BASE_PATH=${VITE_BASE_PATH}
ENV VITE_OTEL_ENDPOINT=${VITE_OTEL_ENDPOINT}

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
