FROM python:3.11-slim

# uv for dependency management (matches the host workflow)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first for layer caching (no project install — this is an app, not a package)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Application code: root entrypoint + config, plus the models, agent, backend, and evals packages
COPY config.py main.py ./
COPY models/ ./models/
COPY agent/ ./agent/
COPY backend/ ./backend/
COPY evals/ ./evals/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app
EXPOSE 9000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "9000"]
