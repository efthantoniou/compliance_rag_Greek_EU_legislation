# --- build stage ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Next.js bakes rewrites() destinations at build time, so the backend URL must
# be present here (not just at runtime) for the /api proxy to target the right host.
ARG BACKEND_URL=http://localhost:9000
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

# --- run stage ---
FROM node:22-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next ./.next
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/next.config.ts ./next.config.ts
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["npm", "run", "start"]
