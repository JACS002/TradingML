<div align="center">

# 📈 TradingML: End-to-End Algorithmic Trading Pipeline

**A production-grade Machine Learning system for financial market prediction, featuring a fully automated data pipeline, predictive modeling, and a containerized inference API.**

[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-Models-EB4223?style=for-the-badge&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io/)

[System Architecture](#-system-architecture) • [Key Features](#-key-features) • [Data Pipeline](#-data-pipeline--engineering) • [ML Strategy](#-machine-learning-strategy) • [Deployment](#-deployment-inference-api) • [Quick Start](#-quick-start-guide)

</div>

---

## 📋 Overview

This project demonstrates a complete **Data Product lifecycle**: from raw data ingestion and robust feature engineering to model training, backtesting, and deployment. It is designed with a strong focus on **reproducibility, scalability, and idempotency**, orchestrated entirely via **Docker Compose**.

---

## 🏗 System Architecture

The system is designed as a modular pipeline integrating four specialized components:

1. **Data Ingestion Layer**  
   Automated retrieval and normalization of OHLCV market data (`raw.prices_daily`).

2. **Feature Engineering Engine**  
   Transformation of raw data into technical and temporal indicators (`analytics.daily_features`).

3. **Machine Learning Core**  
   Training, validation (Time-Series Split), and optimization of 7 classification algorithms.

4. **Inference API**  
   A containerized REST API serving real-time predictions.

---

## 🧰 Tech Stack

| Component | Technology | Purpose |
|--------|-----------|---------|
| Language | Python 3.10+ | Core logic, data processing, and ML |
| Data Engineering | Pandas, NumPy, SQL | Vectorized computation and structured data manipulation |
| Database | PostgreSQL 15 | Persistent storage (Raw Data Lake & Analytical Warehouse) |
| ML & Analytics | Scikit-learn, XGBoost, LightGBM | Predictive modeling and statistical analysis |
| API Backend | FastAPI, Uvicorn | High-performance ASGI server for inference |
| Infrastructure | Docker, Docker Compose | Containerization and service orchestration |

---

## 🚀 Key Features

- **Idempotent Data Pipeline**  
  Ingestion and feature builder services handle data deduplication and atomic updates, allowing safe re-runs without data corruption.

- **Structured SQL Schemas**  
  Clear separation between `raw` (immutable source data) and `analytics` (enriched ML-ready features).

- **Time-Series Validation**  
  Strict temporal splitting to prevent data leakage:
  - Train: 2019–2022  
  - Validation: 2023  
  - Test: 2024  

- **Production-Ready API**  
  The winning model is serialized and deployed via a documented FastAPI REST endpoint.

---

## ⚙️ Data Pipeline & Engineering

### 1. Ingestion (`raw` schema)

Executed via `01_ingesta_prices_raw.ipynb`.

- **Source**: Yahoo Finance API  
- **Logic**:
  - Downloads daily OHLCV data  
  - Normalizes column names  
  - Stores results in `raw.prices_daily`  
  - Adds metadata (`run_id`, `ingested_at_utc`) for traceability  

---

### 2. Feature Builder (`analytics` schema)

Transforms raw data into a **One Big Table (OBT)** optimized for training.

**Command:**
```bash
docker compose run --rm feature-builder \
  --mode full \
  --ticker AAPL \
  --run-id build_v1 \
  --overwrite true
```

**Engineered Features:**

- **Market Dynamics**
  - Returns: `close-open`, `prev-close`
  - Volatility: 10-day rolling standard deviation

- **Temporal**
  - Cyclical encoding for days and months

- **Lags**
  - All features lagged by `t-1` to strictly avoid data leakage

---

## 🧠 Machine Learning Strategy

Implemented in `ml_trading_classifier.ipynb`.

### Problem Definition

- **Binary Classification**
- Target: `Close(t) > Open(t)`
- Constraint: Only information available at `Open(t)` is used

### Model Selection & Validation

- Benchmarked **7 algorithms**, including:
  - Logistic Regression
  - Random Forest
  - XGBoost
  - LightGBM

- **Baseline**: Majority class classifier  
- **Optimization**: `GridSearchCV` with strict time-series cross-validation  
- **Winner**: **Logistic Regression**, optimized for **F1-score and stability**

---

### Financial Backtesting

Beyond ML metrics, the model was evaluated using a financial simulation on unseen **Test Data (2024)**.

- **Strategy**:
  - Long position if `prediction = 1`
  - Cash if `prediction = 0`

- **Outcome**:
  - Equity curve compared against a **Buy & Hold** benchmark

---

## ⚡ Deployment (Inference API)

The final model is serialized (`.pkl`) and embedded into a **FastAPI** microservice.

### Run the API

```bash
docker compose build model_api
docker compose up -d model_api
```

### Usage

- **Endpoint**: `POST /predict`
- **Payload**:
```json
{
  "feat_ret_co_prev": 0.01,
  "feat_ret_prevclose_prev": 0.02,
  "feat_vol10_prev": 0.05,
  "feat_volume_prev": 55000000,
  "ticker": "AAPL",
  "day_of_week": 3,
  "month": 12
}
```

- **Swagger UI**:  
  http://localhost:8000/docs

---

## 🛠 Quick Start Guide

### Prerequisites

- Docker  
- Docker Compose  

Create environment variables:
```bash
cp .env.example .env
```

### Execution Steps

1. **Initialize Infrastructure**
```bash
docker compose up -d postgres jupyter
```

2. **Run Ingestion**
- Open Jupyter at `http://localhost:8888`
- Execute `01_ingesta_prices_raw.ipynb`

3. **Build Features**
```bash
docker compose run --rm feature-builder --mode full --ticker AAPL --run-id init
```

4. **Train Model**
- Run `ml_trading_classifier.ipynb`
- Generates `models/best_model.pkl`

5. **Deploy API**
```bash
docker compose up -d model_api
```

---

## 🔮 Future Improvements (AI-Native Roadmap)

- Integration of **LLMs (e.g., GPT-4)** to analyze financial news sentiment as an additional feature
- Automated re-training pipeline using **Airflow** or **Prefect**

---

## 📌 License

This project is intended for educational and research purposes.
