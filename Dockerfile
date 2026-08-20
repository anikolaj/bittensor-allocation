FROM python:3.11-slim-bookworm

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY fixtures ./fixtures

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

ENTRYPOINT ["python", "src/main.py"]
