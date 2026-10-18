FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.7.3 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN --mount=type=secret,id=cloud_proxy_ca \
    if [ -s /run/secrets/cloud_proxy_ca ]; then \
      cp /run/secrets/cloud_proxy_ca /usr/local/share/ca-certificates/cloud-proxy.crt && update-ca-certificates; \
    fi && UV_NATIVE_TLS=true uv sync --frozen --no-dev
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
