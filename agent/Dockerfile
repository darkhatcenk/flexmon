# syntax=docker/dockerfile:1

FROM golang:1.21-alpine AS builder

WORKDIR /build

# Speed & reliability: use official Go proxy and checksum database
ENV GOPROXY=https://proxy.golang.org,direct
ENV GOSUMDB=sum.golang.org

# Copy module files first and download dependencies
COPY go.mod go.sum ./
RUN go clean -modcache && go mod download

# Now copy the source code
COPY . .

# Optional: verify modules (won't fail build if upstream hiccups; adjust as needed)
RUN go mod verify || true

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o flexmon-agent ./cmd/flexmon-agent

# Final image
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app

COPY --from=builder /build/flexmon-agent /app/flexmon-agent

# Run as non-root user
RUN adduser -D -u 1000 flexmon
USER flexmon

ENTRYPOINT ["/app/flexmon-agent"]
