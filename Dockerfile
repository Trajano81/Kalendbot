FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para html2image (JPEG export)
RUN apt-get update && \
    apt-get install -y --no-install-recommends chromium && \
    rm -rf /var/lib/apt/lists/*

ENV CHROMIUM_PATH=/usr/bin/chromium

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ src/

# Puerto del webhook (interno, no expuesto al host)
EXPOSE 8000

CMD ["python", "-m", "src.server"]
