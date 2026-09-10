# ShopLite API: gunicorn serving the Flask app on $SHOPLITE_PORT.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first so code changes don't re-download them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY shoplite ./shoplite
COPY migrations ./migrations
COPY scripts ./scripts
COPY fixtures ./fixtures
COPY sql ./sql
RUN uv sync --frozen --no-dev

RUN useradd --create-home shoplite && mkdir -p instance && chown shoplite instance
USER shoplite
ENV PATH="/app/.venv/bin:$PATH" FLASK_APP=shoplite SHOPLITE_PORT=5000
EXPOSE 5000
HEALTHCHECK --interval=10s --timeout=3s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"SHOPLITE_PORT\"]}/healthz', timeout=2)"

# One worker so /metrics counts every request (metrics live in the process).
CMD ["sh", "-c", "flask db upgrade && exec gunicorn --bind 0.0.0.0:${SHOPLITE_PORT} --workers 1 --threads 4 'shoplite:create_app()'"]
