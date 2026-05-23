FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

EXPOSE 8000

# Use the Socket.io-wrapped ASGI app
CMD ["uvicorn", "app.main:asgi_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
