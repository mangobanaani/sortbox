# Stage 1: Build frontend
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Copy backend source
COPY src/ src/

# Copy config
COPY labels.yaml .

# Copy built frontend from stage 1
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Create data directory for SQLite (for future orchestrator features)
RUN mkdir -p /app/data

ENV DATABASE_PATH=/app/data/sortbox.db
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
