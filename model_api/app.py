# model_api/app.py

import os
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

# ============================================================
# Config
# ============================================================

MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    "models/best_model_LogisticRegression.pkl"
)

app = FastAPI(
    title="Trading Daily Classifier API",
    description="API de predicción diaria (sube/no sube) basada en Regresión Logística.",
    version="1.0.0",
)

# ============================================================
# Carga del modelo al iniciar el servidor
# ============================================================

@app.on_event("startup")
def load_model():
    global model
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"No se encontró el modelo en {MODEL_PATH}. "
            "Asegúrate de que el archivo exista y el Dockerfile lo copie correctamente."
        )
    model = joblib.load(MODEL_PATH)
    print(f" Modelo cargado desde: {MODEL_PATH}")


# ============================================================
# Esquema de entrada (features diarios)
# Ajustado a las columnas que usaste en df_ml para X
# ============================================================

class DailyFeatures(BaseModel):
    ticker: Literal["AAPL", "MSFT", "TSLA"] = Field(..., description="Ticker del activo")
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    day_of_week: int = Field(..., ge=0, le=6, description="0=Lunes, 6=Domingo")
    feat_ret_co_prev: float = Field(..., description="Retorno close-open del día previo")
    feat_ret_prevclose_prev: float = Field(..., description="Retorno close-close del día previo")
    feat_vol10_prev: float = Field(..., description="Volatilidad (rolling 10 días) previa")
    feat_volume_prev: float = Field(..., description="Volumen del día previo")


class PredictionResponse(BaseModel):
    ticker: str
    predicted_label: int
    predicted_class: Literal["down", "up"]
    prob_down: float
    prob_up: float


# ============================================================
# Endpoints
# ============================================================

@app.get("/health")
def healthcheck():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(features: DailyFeatures):
    """
    Recibe las features diarias de un activo y devuelve:
    - etiqueta predicha (0=down, 1=up)
    - probabilidad de cada clase
    """
    # Convertir a DataFrame con las columnas que espera el pipeline
    input_df = pd.DataFrame([features.dict()])

    # Predicción
    y_pred = model.predict(input_df)[0]

    # Probabilidades (si el modelo las soporta)
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(input_df)[0]
        prob_down = float(proba[0])
        prob_up = float(proba[1])
    else:
        # fallback: sin probas reales, usamos 0/1
        prob_down = float(1 - y_pred)
        prob_up = float(y_pred)

    return PredictionResponse(
        ticker=features.ticker,
        predicted_label=int(y_pred),
        predicted_class="up" if int(y_pred) == 1 else "down",
        prob_down=prob_down,
        prob_up=prob_up,
    )
