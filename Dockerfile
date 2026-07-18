# Stage 1: Build the Next.js frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Stage 2: Setup FastAPI and serve
FROM python:3.13-slim
WORKDIR /app

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/out ./frontend/out

# Render dynamically assigns a port, but defaults to 10000 if not specified
ENV PORT=10000

CMD ["sh", "-c", "uvicorn backend.src.api.app:app --host 0.0.0.0 --port ${PORT}"]
