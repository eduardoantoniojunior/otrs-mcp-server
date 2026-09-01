FROM python:3.12.8-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml ./
COPY uv.lock ./
COPY src ./src/

RUN uv venv && \
    uv pip install . && \
    uv pip install opentelemetry-instrumentation-httpx \
                   opentelemetry-instrumentation-logging

FROM python:3.12.8-slim-bookworm

WORKDIR /app

RUN groupadd -r otrs && useradd -r -g otrs otrs

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY pyproject.toml /app/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src" \
    PYTHONFAULTHANDLER=1

RUN mkdir -p /data && chown -R otrs:otrs /app /data
USER otrs

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.connect(('localhost', 8001)); s.close()" || exit 1

# Zero-code: opentelemetry-instrument wraps o MCP server
CMD ["opentelemetry-instrument", "python", "-m", "otrs_mcp.main"]

LABEL org.opencontainers.image.title="OTRS MCP Server" \
      org.opencontainers.image.description="Model Context Protocol server for OTRS integration" \
      org.opencontainers.image.version="0.2.0" \
      org.opencontainers.image.authors="Eduardo Antonio" \
      org.opencontainers.image.source="https://github.com/eduardoantoniojunior/otrs-mcp-server" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.vendor="BeOnUp"
