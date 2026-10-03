FROM python:3.11-slim

WORKDIR /app

# Runtime libs that opencv-python-headless / easyocr need even "headless".
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /data is where the Fly volume is mounted - inventory.db lives there so
# it survives deploys and restarts instead of the container's throwaway disk.
ENV INVENTORY_DB_PATH=/data/inventory.db
RUN mkdir -p /data /app/uploads

EXPOSE 8080

# Single worker: EasyOCR loads a sizable model into memory per worker,
# and small VM sizes can't afford to multiply that. Long timeout because
# OCR + the AI calls routinely take 10-20+ seconds.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "2", "--timeout", "120", "app:app"]
