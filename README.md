# TradingML Pipeline - Sistema Completo de Predicción de Mercados

Este proyecto implementa un pipeline completo de Machine Learning para trading algorítmico, que abarca desde la ingesta de datos de mercado hasta el despliegue de modelos predictivos mediante una API REST. El sistema procesa precios diarios de mercado, genera features avanzadas, entrena modelos de clasificación para predicción de dirección diaria, y permite simular estrategias de inversión.

## Componentes del Sistema

El pipeline se compone de tres módulos integrados:

1. **Ingesta de Datos**: Descarga y almacena datos OHLCV desde Yahoo Finance en el esquema `raw.prices_daily`
2. **Construcción de Features**: Servicio CLI (`feature-builder`) que genera la tabla analítica `analytics.daily_features` 
3. **Modelado y Predicción**: Entrenamiento de modelos de ML, simulación de inversión y API REST para inferencia
4. **Infraestructura**: Entorno dockerizado con PostgreSQL, Jupyter Notebook y servicios de procesamiento

---

## 1. Arquitectura General

El entorno se ejecuta mediante Docker Compose con los siguientes servicios:

| Servicio          | Descripción                                                         |
|------------------|---------------------------------------------------------------------|
| postgres         | Base de datos que almacena los esquemas `raw` y `analytics`.        |
| jupyter-notebook | Entorno para ejecutar notebooks de ingesta y validación.            |
| feature-builder  | Servicio encargado de generar las features en `analytics`.          |

La comunicación entre servicios se realiza mediante redes internas definidas por Docker.

---

## 2. Configuración del Sistema

### Variables de Ambiente

El proyecto utiliza un archivo `.env` ubicado en la raíz. A continuación se muestra un ejemplo:

```env
PG_HOST=postgres
PG_PORT=5432
PG_DB=trading_db
PG_USER=postgres
PG_PASSWORD=postgres

PG_SCHEMA_RAW=raw
PG_SCHEMA_ANALYTICS=analytics

TICKERS=AAPL,MSFT,TSLA
START_DATE=2018-01-01
END_DATE=2024-12-31
RUN_ID=init_ingest
```
Copiar el archivo base:

```bash
cp .env.example .env
```

---

## 3. Pipeline de Datos

### 3.1 Ingesta de Datos de Mercado

La ingesta de datos se realiza mediante el notebook `01_ingesta_prices_raw.ipynb`, que constituye el primer paso del pipeline. Este proceso:

- **Obtiene datos históricos**: Descarga precios diarios OHLCV desde Yahoo Finance para los tickers especificados en la configuración
- **Normaliza estructura**: Estandariza nombres de columnas (open, high, low, close, adj_close, volume)
- **Almacena en base de datos**: Inserta los datos en la tabla `raw.prices_daily` con metadatos de trazabilidad
- **Garantiza idempotencia**: Permite re-ejecuciones seguras mediante estrategias de reemplazo o adición
- **Registra metadatos**: Incluye `run_id` e `ingested_at_utc` para auditoría y versionado

Este paso es prerequisito para la construcción de features y debe completarse antes de continuar con el pipeline.

### 3.2 Construcción de Features Analíticas

El módulo `feature-builder` transforma los datos brutos en features listas para modelado, generando la tabla analítica `analytics.daily_features` mediante un proceso automatizado y escalable.

**Ejecución:**
```bash
docker compose run --rm feature-builder \
  --mode full \
  --ticker AAPL \
  --run-id build_v1 \
  --overwrite true
```

**Proceso de construcción:**

El servicio automatiza la generación de features mediante:

- **Preparación del esquema**: Crea los esquemas `raw` y `analytics` si no existen
- **Extracción de datos**: Lee precios históricos desde `raw.prices_daily`
- **Ingeniería de features**: Calcula indicadores técnicos y variables temporales:
  - Descriptores temporales: `year`, `month`, `day_of_week`
  - Precios de mercado: `open`, `high`, `low`, `close`, `volume`
  - Retornos: `return_close_open`, `return_prev_close`
  - Volatilidad: `volatility_10d` (ventana móvil de 10 días)
- **Almacenamiento controlado**: Inserta en `analytics.daily_features` con manejo inteligente de duplicados

### 3.3 Estructura de la Tabla Analítica

La tabla generada contiene las siguientes columnas:

| Columna                  | Descripción                                     |
| ------------------------ | ----------------------------------------------- |
| date                     | Fecha del día bursátil                          |
| ticker                   | Activo                                          |
| year, month, day_of_week | Descriptores temporales                         |
| open, high, low, close   | Precios diarios                                 |
| volume                   | Volumen transado                                |
| return_close_open        | (close - open) / open                           |
| return_prev_close        | close_t / close_{t-1} - 1                       |
| volatility_10d           | Desviación estándar de retornos rolling 10 días |
| run_id                   | Identificador de la corrida                     |
| ingested_at_utc          | Fecha de generación del registro (UTC)          |

La estructura corresponde a un One Big Table con una fila por día por activo.

---

## 4. Garantías de Calidad y Reproducibilidad

### 4.1 Idempotencia del Sistema

El feature-builder garantiza idempotencia mediante:

1. Conteo previo de filas existentes para el ticker y rango.

2. Eliminación de filas existentes cuando --overwrite=true.

3. Inserción controlada de las nuevas features.

4. Registro de logs que muestran:

    - Número de filas procesadas.

    - Rango efectivo de fechas.

    - Cantidad de filas insertadas.

    - Cantidad de filas eliminadas (si aplica).

Este enfoque asegura reproducibilidad del pipeline.

### 4.2 Validación del Pipeline

Luego de ejecutar la ingesta y el feature-builder, se deben validar:

- Conteo de filas en raw.prices_daily.

- Rango de fechas.

- Conteo de features generadas.

- Verificación de que analytics.daily_features contiene una fila por día por activo.

- Validación mediante consultas SQL o carga de datos en notebooks posteriores.

---

## 5. Machine Learning y Modelado Predictivo

La tabla `analytics.daily_features` alimenta el módulo de Machine Learning, implementado en `ml_trading_classifier.ipynb`, que desarrolla un sistema completo de predicción de dirección diaria del mercado mediante clasificación binaria. El sistema incluye entrenamiento de múltiples algoritmos, validación temporal, simulación de estrategias de inversión y despliegue productivo mediante API REST.

### 5.1 Definición del Problema de Predicción

Dado un día bursátil t y un activo determinado, se busca predecir:

```bash
target_up = 1 si close > open
target_up = 0 en caso contrario
```

El objetivo es anticipar si el día cerrará al alza, utilizando únicamente información disponible al inicio de ese mismo día para evitar leakage. El target provee una señal básica de dirección, apta para estrategias de trading sin predicción de magnitud de precios.

### 5.2 Preparación de Datos para Modelado

Los datos se cargan directamente desde PostgreSQL utilizando los esquemas construidos en el Proyecto 06, específicamente:

- `raw.prices_daily`
- `analytics.daily_features`

El notebook establece conexión mediante variables de entorno y extrae las columnas necesarias desde: analytics.daily_features


incluyendo año, mes, día de la semana, precios de mercado, retornos lag y volatilidad.

### 5.3 Ingeniería de Features y Target

A partir de la columna `close` y `open`, se construye:

- `target_up`

Para cada día t, se definen las features exclusivamente con información conocida hasta t−1. Estas incluyen:

- `feat_ret_co_prev`: retorno close–open del día anterior
- `feat_ret_prevclose_prev`: retorno del cierre anterior
- `feat_vol10_prev`: volatilidad 10 días previa
- `feat_volume_prev`: volumen del día anterior
- Features categóricas: `ticker`, `day_of_week`, `month`

Se elimina cualquier fila con valores nulos tras aplicar los desplazamientos (lags).

No se utiliza ninguna información del cierre de t para evitar leakage.

### 5.4 Estrategia de Validación Temporal

Se emplea un split basado estrictamente en tiempo:

- **Train:** 2019–2022  
- **Validación:** 2023  
- **Test:** 2024  

Este enfoque garantiza que la validación y el test utilizan solamente datos de períodos posteriores y nunca mezclan información futura en la fase de entrenamiento.

### 5.5 Pipeline de Preprocesamiento

El preprocesamiento se implementa mediante un `ColumnTransformer`, con:

- Pipeline numérico:
  - Imputación por mediana
  - Escalado con `StandardScaler`

- Pipeline categórico:
  - Imputación por moda
  - One-hot encoding

El preprocesador es parte explícita del pipeline de cada modelo, lo que garantiza reproducibilidad y evita inconsistencias en inferencia.

### 5.6 Entrenamiento y Comparación de Modelos

Se implementaron al menos siete modelos siguiendo las especificaciones del curso:

1. Logistic Regression  
2. Linear SVC  
3. Decision Tree  
4. Random Forest  
5. Gradient Boosting  
6. XGBoost  
7. LightGBM  

Cada modelo se entrena mediante un `Pipeline(preprocessor + model)` y utiliza un `GridSearchCV` con validación temporal. Se registran métricas de:

- Accuracy  
- Precision  
- Recall  
- F1  
- ROC-AUC  
- Matriz de confusión  

Se construye una tabla comparativa con los mejores hiperparámetros de cada modelo y su desempeño en Train, Validación y Test.

### 5.7 Modelo Baseline y Benchmarking

Se implementa un baseline obligatorio:

`Predicción constante = clase mayoritaria`


Sus métricas se comparan con las del modelo ganador, demostrando que un F1 alto para la clase positiva no necesariamente implica utilidad para trading debido al sesgo hacia días alcistas.

### 5.8 Selección del Modelo Óptimo

Se selecciona el modelo con mejor F1 en validación manteniendo simplicidad y consistencia temporal.  
En este caso, el modelo ganador fue:

**Logistic Regression**, con los hiperparámetros optimizados según la búsqueda.

El modelo final se reentrena sobre Train + Validación y se evalúa después en Test (2024).

### 5.9 Análisis de Errores y Diagnóstico

Se realiza un análisis detallado de errores del modelo en el período de Test 2024:

- Errores por ticker  
- Errores por mes  
- Errores por cuartiles de volatilidad previa  
- Matrices de confusión por grupo  
- Evaluación de probabilidades (`predict_proba`) en días incorrectos  

El análisis identifica sesgos importantes del modelo hacia predicción de días alcistas, así como dificultades en períodos de alta volatilidad y en activos con comportamiento más inestable.

### 5.10 Simulación de Estrategia de Inversión

Con el modelo ganador se simula una estrategia simple para el año de Test (2024):

- Capital inicial: USD 10,000  
- Si `pred = 1`: posición larga en el activo  
- Si `pred = 0`: efectivo  
- Benchmark: Buy & Hold  
- Sin costos de transacción, sin apalancamiento  

El notebook genera:

- Curva de capital (`equity curve`)  
- Capital final  
- Retorno total y comparativo  
- Número de días en posición  

El análisis conecta directamente las métricas de ML con la rentabilidad real obtenida en el backtest.

---

## 6. Despliegue y Producción

### 6.1 Serialización del Modelo

El modelo ganador se serializa en:

`models/best_model_LogisticRegression.pkl`


Este archivo contiene:

- Preprocesador completo
- Modelo entrenado
- Hiperparámetros finales

El archivo puede cargarse directamente en producción sin necesidad de repetir el entrenamiento.

### 6.2 API REST para Inferencia

El directorio `model_api/` contiene:

- `app.py` (implementación FastAPI)
- `Dockerfile` para empaquetar el servicio
- Carga del modelo mediante la variable de ambiente `MODEL_PATH`

El endpoint principal es:

`POST /predict`


El cuerpo esperado incluye las features necesarias para una observación.  
La respuesta retorna la predicción binaria y la probabilidad correspondiente.

### 6.3 Despliegue del Servicio

Construcción de la imagen:

```bash
docker compose build model_api
```

Ejecución del servicio:

```bash
docker compose up -d model_api
```

Endpoint disponible en:

```bash
http://localhost:8080/predict
```
Ejemplo(cURL):

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"feat_ret_co_prev":0.01,"feat_ret_prevclose_prev":0.02,"feat_vol10_prev":0.05,"feat_volume_prev":55000000,"ticker":"AAPL","day_of_week":3,"month":12}'
```
---

## 7. Características del Sistema

### 7.1 Reproducibilidad y Mantenibilidad

El proyecto incluye:

- .env.example

- Estructura de carpetas modular (ml, model_api, feature_builder)

- Pipelines completos serializados

- Ejemplos de ejecución de Docker y del pipeline de ML

- Scripts y notebooks alineados con la secuencia del curso

Cada componente puede ejecutarse desde cero siguiendo únicamente Docker Compose y el notebook principal.

### 7.2 Resumen del Sistema

TradingML Pipeline constituye una solución integral para predicción de mercados financieros que integra:

**Pipeline de Datos:**
- Ingesta automatizada de datos de mercado desde Yahoo Finance
- Construcción de features técnicas y temporales mediante procesamiento distribuido
- Almacenamiento estructurado en base de datos PostgreSQL con esquemas optimizados

**Sistema de Machine Learning:**
- Entrenamiento y comparación de 7 algoritmos de clasificación
- Validación temporal estricta para evitar data leakage
- Selección automatizada del modelo óptimo basada en métricas de negocio

**Simulación y Evaluación:**
- Backtesting de estrategias de inversión con capital simulado
- Análisis detallado de errores y diagnóstico del modelo
- Comparación con estrategias benchmark (Buy & Hold)

**Despliegue Productivo:**
- API REST dockerizada para inferencia en tiempo real  
- Documentación interactiva y interfaz de pruebas
- Arquitectura escalable y lista para producción

El sistema representa una implementación completa de MLOps aplicado a finanzas cuantitativas, desde la ingesta hasta el despliegue, con énfasis en reproducibilidad y calidad del código.

---

## 8. Guía de Ejecución Completa

Para reproducir todo el sistema desde la ingesta hasta la API, se recomienda seguir los pasos descritos a continuación.

---

### 8.1 Preparación del Entorno

Crear el archivo `.env` a partir de `.env.example` y asegurarse de que Docker Desktop esté en ejecución.  
Los servicios se levantarán mediante `docker compose`.

---

### 8.2 Inicialización de Servicios

Iniciar PostgreSQL y Jupyter Notebook con:

- `docker compose up -d postgres`  
- `docker compose up -d jupyter`

Esto habilita la base de datos y el entorno de notebooks.

---

### 8.3 Ejecución del Pipeline de Datos

Abrir `http://localhost:8888` y ejecutar el notebook `01_ingesta_prices_raw.ipynb`.  
Este proceso descarga los datos OHLCV desde Yahoo Finance y los guarda en `raw.prices_daily`.

---

**Paso 1 - Ingesta de datos:**
Abrir `http://localhost:8888` y ejecutar el notebook `01_ingesta_prices_raw.ipynb`.  

**Paso 2 - Construcción de features:**

Ejecutar el servicio `feature-builder` para cada ticker definido en `.env`, por ejemplo:

`docker compose run --rm feature-builder --mode full --ticker AAPL --run-id build_v1 --overwrite true`

Repetir para los demás activos.  
Este paso genera la tabla OBT `analytics.daily_features`, utilizada para el entrenamiento de modelos.

---

### 8.4 Machine Learning y Modelado

Ejecutar el notebook `ml_trading_classifier.ipynb`.  
En él se realizan las siguientes tareas:

- Carga de datos desde `analytics.daily_features`.  
- Construcción del target sin leakage.  
- División Train–Valid–Test basada en fechas.  
- Entrenamiento y tuning de siete modelos.  
- Comparación de métricas y selección del modelo ganador.  
- Simulación de inversión con USD 10,000.  
- Guardado del modelo final en `models/best_model_LogisticRegression.pkl`.

---

### 8.5 Despliegue de la API

Una vez generado el modelo final, construir la imagen de la API mediante:

`docker compose build model_api`

Iniciar el servicio con:

`docker compose up -d model_api`

La API cargará automáticamente el modelo final.

---

### 8.6 Interacción con el Servicio

La documentación interactiva y la interfaz visual están disponibles en:

`http://localhost:8000/docs`

Desde esta página es posible enviar peticiones al endpoint `/predict` sin necesidad de herramientas externas.

---

### 8.7 Secuencia Completa

El flujo completo del sistema sigue esta secuencia integrada:

1. **Configuración**: Preparar archivo `.env` y levantar infraestructura Docker
2. **Ingesta**: Ejecutar descarga y almacenamiento de datos de mercado  
3. **Feature Engineering**: Construir tabla analítica mediante `feature-builder`
4. **Machine Learning**: Entrenar, evaluar y seleccionar modelo óptimo
5. **Serialización**: Guardar modelo final para producción
6. **Containerización**: Construir imagen de la API de inferencia
7. **Despliegue**: Levantar servicio REST y documentación interactiva
8. **Validación**: Probar predicciones mediante interfaz web

Esta arquitectura garantiza la trazabilidad completa desde datos brutos hasta predicciones productivas, con reproducibilidad total del experimento y facilidad de despliegue en cualquier entorno compatible con Docker.
