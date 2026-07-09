#!/bin/bash

# 1. Start the FastAPI API Service in the background
echo "Starting FastAPI REST Backend on http://127.0.0.1:8000..."
python3 -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 > fastapi.log 2>&1 &

# 2. Wait for the API backend to become ready
echo "Waiting for models to load and API to bind to port 8000..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/api/v1/health | grep -q "healthy"; then
        echo "FastAPI Backend is online!"
        break
    fi
    sleep 2
done

# 3. Start the Streamlit frontend in the foreground (Hugging Face binds to port 7860)
echo "Starting Streamlit Intelligence Hub on port 7860..."
streamlit run app.py --server.port 7860 --server.address 0.0.0.0
