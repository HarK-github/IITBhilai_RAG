# Stage 1: Build the Next.js frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy all frontend files and build static export
COPY frontend/ .
RUN npm run build

# Stage 2: Setup FastAPI and serve
FROM python:3.13-slim
WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code and pre-populated Chroma DB
COPY backend/ ./backend/

# Copy built frontend files from Stage 1
COPY --from=frontend-builder /app/frontend/out ./frontend/out

# Hugging Face exposes port 7860
EXPOSE 7860

# We need to make sure we set the port and host for Hugging Face
ENV PORT=7860
ENV HOST=0.0.0.0

# Run the FastAPI server on port 7860
CMD ["uvicorn", "backend.src.api.app:app", "--host", "0.0.0.0", "--port", "7860"]
