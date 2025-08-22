# Case Outcome Predictor

End-to-end example with three parts:
- Train a text model from case summaries (TF-IDF + Logistic Regression).
- Serve predictions via a FastAPI backend.
- Simple browser frontend to enter a summary and see prediction + confidence.

## Prerequisites
- Python 3.10+ installed on Windows
- PowerShell

## Install dependencies

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install --upgrade pip; pip install -r requirements.txt
```

## 1) Train the model
This reads `data/case_data.csv`, trains TF‑IDF + Logistic Regression, and saves `models/model.pkl` and `models/vectorizer.pkl`.

```powershell
.\.venv\Scripts\Activate.ps1; python train_model.py
```

## 2) Start the backend API
Runs FastAPI with CORS enabled and a `/predict` endpoint.

```powershell
.\.venv\Scripts\Activate.ps1; uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

- Open docs at: http://127.0.0.1:8000/docs

## 3) Open the frontend
Open `frontend/index.html` in your browser. It sends requests to `http://127.0.0.1:8000/predict`.

## Tests
Run unit tests for training and API.

```powershell
.\.venv\Scripts\Activate.ps1; pytest -q
```

## Notes
- If the backend starts without model files present, it will attempt to train from `data/case_data.csv` on startup.
- The included CSV is a tiny sample for demonstration; replace it with your real dataset (columns: `summary`, `outcome`).
