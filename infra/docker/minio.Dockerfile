# syntax=docker/dockerfile:1.7
# Upstream image trả 401 và binary archive trả 410 ở lượt kiểm chứng Prompt 03.
# Build từ official commit + source tar SHA-256, giữ nguyên stack MinIO.
FROM golang:1.25.3-bookworm AS build
ENV GOTOOLCHAIN=local
ADD --checksum=sha256:8819e3e7817e46b7b3798f8f200ead208562e571563c2e040352378031abe9f2 https://codeload.github.com/minio/minio/tar.gz/07c3a429bfed433e49018cb0f78a52145d4bedeb /tmp/minio.tar.gz
WORKDIR /src
RUN tar -xzf /tmp/minio.tar.gz --strip-components=1
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -buildvcs=false -trimpath -ldflags='-s -w' -o /minio .
FROM alpine:3.22.2
COPY --from=build /minio /usr/local/bin/minio
COPY --from=build /src/LICENSE /licenses/LICENSE
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
LABEL org.opencontainers.image.source="https://github.com/minio/minio" \
      org.opencontainers.image.revision="07c3a429bfed433e49018cb0f78a52145d4bedeb"
RUN addgroup -g 10001 minio && adduser -D -u 10001 -G minio minio && mkdir /data && chown minio:minio /data
USER minio
EXPOSE 9000
ENTRYPOINT ["/usr/local/bin/minio"]
CMD ["server", "/data", "--console-address", ":9001"]
