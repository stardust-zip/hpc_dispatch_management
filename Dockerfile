FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get update \
    && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8888

CMD ["uvicorn", "src.hpc_dispatch_management.main:app", "--host", "0.0.0.0", "--port", "8888"]
