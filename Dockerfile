# Multi-stage Dockerfile for Hugging Face Spaces & Production Cloud Containers
# 1. Build Frontend Production Bundle
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# 2. Production Python Backend & Static SPA Host
FROM python:3.11-slim

# Install essential system libraries for CP-SAT solver and document parsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set up user with UID 1000 for Hugging Face Spaces security
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PORT=7860 \
    HOST=0.0.0.0

WORKDIR /home/user/app

# Install python dependencies from pyproject.toml
COPY --chown=user pyproject.toml ./
RUN pip install --no-cache-dir --user -e .

# Copy application source and seed fixtures
COPY --chown=user backend/ ./backend/
COPY --chown=user fixtures/ ./fixtures/
COPY --chown=user scripts/ ./scripts/

# Copy compiled frontend SPA from builder stage
COPY --chown=user --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ingest baseline 1,800 student records into SQLite
RUN python scripts/load_all_1800_students.py

# Expose server port (Hugging Face Spaces uses 7860)
EXPOSE 7860

# Start unified server
CMD ["python", "scripts/lan_launcher.py"]
