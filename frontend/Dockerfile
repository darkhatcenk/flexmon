FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files (both package.json and package-lock.json if it exists)
COPY package*.json ./

# Install dependencies with fallback: use npm ci if lock file exists, otherwise npm install
RUN if [ -f package-lock.json ]; then \
      echo "Found package-lock.json, using npm ci..."; \
      npm ci --no-audit --no-fund; \
    else \
      echo "No package-lock.json found, using npm install..."; \
      npm install --no-audit --no-fund; \
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
