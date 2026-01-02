#!/bin/bash

# Startup script for Hugging Face Spaces
# Runs both backend (FastAPI) and frontend (Streamlit) in the same container

# Start backend in background
echo "Starting backend API server..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 5

# Check backend health
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    echo "Waiting for backend... ($i/30)"
    sleep 2
done

# Start frontend on port 7860 (Hugging Face Spaces requirement)
echo "Starting Streamlit frontend..."
streamlit run frontend/app.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
