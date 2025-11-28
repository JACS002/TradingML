import os
import argparse
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError


from utils_db import get_engine, ensure_schemas


def parse_args():
    parser = argparse.ArgumentParser(
        description="Construye analytics.daily_features a partir de raw.prices_daily"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "by-date-range"],
        required=True,
        help="full: recrea features para todo el ticker; by-date-range: solo para un rango de fechas",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        required=True,
        help="Ticker a procesar (ej. AAPL)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Fecha inicio (YYYY-MM-DD). Opcional en modo full.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Fecha fin (YYYY-MM-DD). Opcional en modo full.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Identificador de esta corrida de feature-building",
    )
    parser.add_argument(
        "--overwrite",
        type=str,
        choices=["true", "false"],
        default="true",
        help="Si 'true', sobrescribe filas existentes para (ticker, date) en el rango dado",
    )
    return parser.parse_args()


def load_raw_prices(engine, schema_raw, ticker, mode, start_date, end_date):
    """
    Lee raw.prices_daily desde Postgres para el ticker y rango solicitados.
    Si mode == 'full' y no se dan fechas, toma el rango completo disponible.
    """
    if mode == "full":
        if start_date is None or end_date is None:
            q_range = text(
                f"""
                SELECT MIN(date) AS min_date, MAX(date) AS max_date
                FROM {schema_raw}.prices_daily
                WHERE ticker = :ticker
                """
            )
            with engine.connect() as conn:
                res = conn.execute(q_range, {"ticker": ticker}).mappings().first()
            if res is None or res["min_date"] is None:
                raise ValueError(f"No hay datos en raw.prices_daily para ticker={ticker}")
            start_date = res["min_date"]
            end_date = res["max_date"]

    if start_date is None or end_date is None:
        raise ValueError("start_date y end_date no pueden ser None en by-date-range")

    query_raw = text(
        f"""
        SELECT
            date,
            ticker,
            open,
            high,
            low,
            close,
            adj_close,
            volume
        FROM {schema_raw}.prices_daily
        WHERE ticker = :ticker
          AND date BETWEEN :start_date AND :end_date
        ORDER BY date
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql(
            query_raw,
            conn,
            params={"ticker": ticker, "start_date": start_date, "end_date": end_date},
        )

    return df, pd.to_datetime(start_date), pd.to_datetime(end_date)


def compute_features(df_raw, run_id):
    """Construye las columnas requeridas para analytics.daily_features."""
    if df_raw.empty:
        raise ValueError("DataFrame raw vacío, no hay nada que procesar.")

    df = df_raw.copy()
    df["date"] = pd.to_datetime(df["date"])

    # Ordenar por fecha por seguridad
    df = df.sort_values("date").reset_index(drop=True)

    # Identificación de día
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek  # 0=lunes

    # Features de mercado
    df["return_close_open"] = (df["close"] - df["open"]) / df["open"]

    df["close_lag1"] = df["close"].shift(1)
    df["return_prev_close"] = df["close"] / df["close_lag1"] - 1

    # Volatilidad n-días (ejemplo: 10 días de retornos diarios)
    df["daily_return"] = df["close"].pct_change()
    window_n = 10
    df["volatility_10d"] = df["daily_return"].rolling(window_n).std()

    # Metadatos
    ingested_at = datetime.now(timezone.utc)
    df["run_id"] = run_id
    df["ingested_at_utc"] = ingested_at

    # Eliminamos filas sin suficiente historial (lag/rolling)
    df_feat = df.dropna(subset=["close_lag1", "volatility_10d"]).copy()

    # Seleccionamos columnas finales para analytics.daily_features
    cols_final = [
        "date",
        "ticker",
        "year",
        "month",
        "day_of_week",
        "open",
        "close",
        "high",
        "low",
        "volume",
        "return_close_open",
        "return_prev_close",
        "volatility_10d",
        "run_id",
        "ingested_at_utc",
    ]

    return df_feat[cols_final]


def delete_existing_rows(engine, schema_analytics, ticker, start_date, end_date):
    """Borra filas existentes en analytics.daily_features para (ticker, rango de fechas).
    Si la tabla aún no existe (primer run), no hace nada y devuelve 0.
    """
    delete_sql = text(
        f"""
        DELETE FROM {schema_analytics}.daily_features
        WHERE ticker = :ticker
          AND date BETWEEN :start_date AND :end_date
        """
    )
    try:
        with engine.begin() as conn:
            result = conn.execute(
                delete_sql,
                {
                    "ticker": ticker,
                    "start_date": start_date.date(),
                    "end_date": end_date.date(),
                },
            )
        return result.rowcount
    except ProgrammingError:
        # La tabla no existe todavía -> no hay nada que borrar
        return 0


def count_existing_rows(engine, schema_analytics, ticker, start_date, end_date):
    """Cuenta filas actuales.
    Si la tabla aún no existe, devuelve 0.
    """
    query = text(
        f"""
        SELECT COUNT(*) AS n
        FROM {schema_analytics}.daily_features
        WHERE ticker = :ticker
          AND date BETWEEN :start_date AND :end_date
        """
    )
    try:
        with engine.connect() as conn:
            res = conn.execute(
                query,
                {
                    "ticker": ticker,
                    "start_date": start_date.date(),
                    "end_date": end_date.date(),
                },
            ).scalar()
        return res or 0
    except ProgrammingError:
        # La tabla no existe todavía -> asumimos 0 filas
        return 0



def main():
    args = parse_args()

    schema_raw = os.environ.get("PG_SCHEMA_RAW", "raw")
    schema_analytics = os.environ.get("PG_SCHEMA_ANALYTICS", "analytics")

    engine = get_engine()
    ensure_schemas()

    print("=== Feature Builder ===")
    print(f"Modo: {args.mode}")
    print(f"Ticker: {args.ticker}")
    print(f"Run ID: {args.run_id}")
    print(f"Overwrite: {args.overwrite}")
    if args.start_date or args.end_date:
        print(f"Rango solicitado: {args.start_date} a {args.end_date}")

    # 1) Leer datos crudos
    df_raw, start_date, end_date = load_raw_prices(
        engine,
        schema_raw,
        args.ticker,
        args.mode,
        args.start_date,
        args.end_date,
    )
    print(f"Filas raw leídas: {len(df_raw)}")
    print(f"Rango efectivo: {df_raw['date'].min()} a {df_raw['date'].max()}")

    if df_raw.empty:
        print("No hay datos en raw.prices_daily para ese ticker/rango. Saliendo.")
        return

    # 2) Comportamiento respecto a filas existentes en analytics.daily_features
    n_existing = count_existing_rows(engine, schema_analytics, args.ticker, start_date, end_date)
    print(f"Filas existentes en analytics.daily_features para ese rango: {n_existing}")

    overwrite = args.overwrite.lower() == "true"
    if n_existing > 0 and not overwrite:
        print("overwrite=false y ya existen filas para ese rango. No se modifica nada.")
        return

    # 3) Construir features
    df_features = compute_features(df_raw, args.run_id)
    print(f"Filas de features generadas: {len(df_features)}")

    if df_features.empty:
        print("No se generaron features (posiblemente por poco historial). Saliendo.")
        return

    # 4) Borrar filas existentes (idempotencia) e insertar nuevas
    deleted = delete_existing_rows(engine, schema_analytics, args.ticker, start_date, end_date)
    print(f"Filas borradas en analytics.daily_features: {deleted}")

    df_features.to_sql(
        "daily_features",
        engine,
        schema=schema_analytics,
        if_exists="append",      # siempre agregamos, tras borrar lo anterior
        index=False,
    )
    print(f"Filas insertadas en analytics.daily_features: {len(df_features)}")
    print("=== Fin del feature builder ===")


if __name__ == "__main__":
    main()
