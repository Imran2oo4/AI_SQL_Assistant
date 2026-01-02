# Hugging Face Space Dockerfile
# Combines backend + frontend in single container for Spaces deployment

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY rag/ ./rag/
COPY pipeline/ ./pipeline/
COPY chromadb_data/ ./chromadb_data/

# Create logs directory
RUN mkdir -p logs backend/logs

# Copy startup script
COPY start_huggingface.sh .
RUN chmod +x start_huggingface.sh

# Expose Streamlit port (Hugging Face Spaces expects port 7860)
EXPOSE 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GROQ_ONLY=true
ENV BACKEND_URL=http://localhost:8000

# Start both services
CMD ["./start_huggingface.sh"]
