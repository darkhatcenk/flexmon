FROM golang:1.21-alpine AS builder

WORKDIR /build

# Copy go module files
COPY go.mod go.sum* ./
RUN go mod download || true

# Copy source code
COPY cmd ./cmd

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -o flexmon-agent ./cmd/flexmon-agent

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app

COPY --from=builder /build/flexmon-agent .

# Run as non-root
RUN adduser -D -u 1000 flexmon
USER flexmon

ENTRYPOINT ["./flexmon-agent"]
