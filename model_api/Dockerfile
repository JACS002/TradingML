# model_api/Dockerfile

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Instalar dependencias
COPY model_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copiar código de la API
COPY model_api/app.py .

# 3. Copiar los modelos entrenados (están en ml/models en tu repo)
COPY ml/models ./models

# 4. Puerto y comando
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
