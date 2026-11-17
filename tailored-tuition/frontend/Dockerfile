# Frontend image: Next.js production server, runs as the non-root `node` user.
# Build context is frontend/.
#
# Base image is pinned to a Node major version and Debian release. For fully
# reproducible builds, pin by digest once you have pulled it:
#   FROM node:22-bookworm-slim@sha256:<digest>

FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# The /api proxy target is baked in at build time.
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=$BACKEND_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-bookworm-slim AS runtime
WORKDIR /app
ARG BACKEND_URL=http://backend:8000
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 BACKEND_URL=$BACKEND_URL
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force
COPY --from=build /app/next.config.mjs ./
COPY --from=build --chown=node:node /app/.next ./.next

USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]
CMD ["node", "node_modules/next/dist/bin/next", "start", "-H", "0.0.0.0", "-p", "3000"]
