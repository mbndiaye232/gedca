FROM python:3.12-slim

# Dépendances système : Tesseract (FR), ocrmypdf, libmagic, postgres client
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      tesseract-ocr-fra \
      ghostscript \
      qpdf \
      unpaper \
      libmagic1 \
      curl \
      build-essential \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installation des dépendances Python
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]"

# Copie du code applicatif
COPY . .

# Dossiers runtime
RUN mkdir -p /app/storage /app/storage/quarantaine /app/storage/inbox

EXPOSE 8000

# Surcharge par docker-compose (api : uvicorn, worker : celery worker, beat : celery beat)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
