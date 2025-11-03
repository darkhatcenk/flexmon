FROM node:18-alpine AS builder

WORKDIR /app

# Enable legacy peer deps for compatibility
ENV NPM_CONFIG_LEGACY_PEER_DEPS=true

# Copy manifest(s)
COPY package*.json ./

# Deterministic install:
# - If package-lock.json exists -> npm ci
# - Else -> generate lock with legacy peer deps, then npm ci
RUN if [ -f package-lock.json ]; then \
      echo "Using existing package-lock.json -> npm ci"; \
      npm ci --no-audit --no-fund; \
    else \
      echo "No lockfile -> generating with legacy peer deps"; \
      npm install --package-lock-only --legacy-peer-deps --no-audit --no-fund; \
      npm ci --no-audit --no-fund; \
    fi

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files from builder to nginx html directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
