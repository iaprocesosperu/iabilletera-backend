FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# La imagen base ya incluye Chromium y todas sus dependencias del sistema
# (Ubuntu Jammy, oficialmente soportada por Playwright), así que no hace
# falta correr "playwright install" aquí.

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
