FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema necesarias para Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala Chromium y sus dependencias del sistema para Playwright
RUN playwright install --with-deps chromium

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
