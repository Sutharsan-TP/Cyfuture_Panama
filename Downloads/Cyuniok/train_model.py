from __future__ import annotations
import os
from pathlib import Path
import joblib
import csv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

DATA_PATH = Path("data/case_data.csv")
MODELS_DIR = Path("models")
MODEL_PATH = MODELS_DIR / "model.pkl"
VECTORIZER_PATH = MODELS_DIR / "vectorizer.pkl"
METADATA_PATH = MODELS_DIR / "metadata.json"

def load_data(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path.resolve()}")
    rows: list[tuple[str, str]] = []
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not {'summary','outcome'}.issubset(reader.fieldnames or []):
            raise ValueError("CSV must have columns: 'summary', 'outcome'")
        for r in reader:
            s = (r.get('summary') or '').strip()
            o = (r.get('outcome') or '').strip()
            if s and o:
                rows.append((s, o))
    if not rows:
        raise ValueError('No valid rows found in CSV')
    return rows

def train(rows: list[tuple[str, str]]):
    X = [s for s, _ in rows]
    y = [o for _, o in rows]

    # Dynamic vectorizer params for small vs larger datasets
    n_docs = len(rows)
    if n_docs < 50:
        vec_kwargs = dict(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 1),
            max_df=0.95,
            min_df=1,
            max_features=None,
        )
    else:
        vec_kwargs = dict(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_df=0.95,
            min_df=2,
            max_features=5000,
        )

    vectorizer = TfidfVectorizer(**vec_kwargs)

    clf = LogisticRegression(max_iter=500, n_jobs=None, class_weight="balanced")

    # If too few samples for stratified split, train on all data and skip validation
    from collections import Counter
    class_counts = Counter(y)
    if len(rows) < 6 or min(class_counts.values()) < 2:
        # Not enough for stratified split
        X_vec = vectorizer.fit_transform(X)
        clf.fit(X_vec, y)
        print("[train] Too few samples for validation split; trained on all data.")
    return clf, vectorizer

    # Build pipeline for convenience during evaluation
    pipeline = Pipeline([
        ("tfidf", vectorizer),
        ("logreg", clf),
    ])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Validation accuracy: {acc:.3f}")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Extract fitted components
    fitted_vectorizer: TfidfVectorizer = pipeline.named_steps["tfidf"]
    fitted_model: LogisticRegression = pipeline.named_steps["logreg"]

    return fitted_model, fitted_vectorizer


def save(model: LogisticRegression, vectorizer: TfidfVectorizer, *, rows: list[tuple[str,str]], training_mode: str) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    print(f"Saved model -> {MODEL_PATH}")
    print(f"Saved vectorizer -> {VECTORIZER_PATH}")
    # Write simple metadata for traceability
    try:
        import json, time
        from collections import Counter
        y = [o for _, o in rows]
        meta = {
            "created_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "labels": list(getattr(model, 'classes_', [])),
            "n_docs": len(rows),
            "class_counts": dict(Counter(y)),
            "training_mode": training_mode,
            "vectorizer": {
                "ngram_range": getattr(vectorizer, 'ngram_range', None),
                "max_df": getattr(vectorizer, 'max_df', None),
                "min_df": getattr(vectorizer, 'min_df', None),
                "max_features": getattr(vectorizer, 'max_features', None),
            },
            "model": {
                "type": type(model).__name__,
                "max_iter": getattr(model, 'max_iter', None),
                "class_weight": getattr(model, 'class_weight', None),
            },
        }
        with METADATA_PATH.open('w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)
        print(f"Saved metadata -> {METADATA_PATH}")
    except Exception as e:
        print(f"[warn] Failed to write metadata: {e}")


if __name__ == "__main__":
    rows = load_data(DATA_PATH)
    model, vectorizer = train(rows)
    # training_mode is inferred based on size threshold used in train()
    training_mode = "all_data" if len(rows) < 6 else "train_test_split"
    save(model, vectorizer, rows=rows, training_mode=training_mode)
