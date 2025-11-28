FROM python:3.10-slim

WORKDIR /app

# Evita que Python genere .pyc y buffer en stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# El entrypoint es el script; los argumentos vienen desde `docker compose run feature-builder -- ...`
ENTRYPOINT ["python", "build_features.py"]
