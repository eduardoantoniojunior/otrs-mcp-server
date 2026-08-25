FROM node:20-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM caddy:2-alpine

COPY --from=builder /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
