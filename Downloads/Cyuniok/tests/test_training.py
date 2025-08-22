from pathlib import Path
import joblib
import pytest

from train_model import load_data, train


def test_training_pipeline(tmp_path: Path):
    # Create tiny dataset
    csv = tmp_path / "case_data.csv"
    csv.write_text(
        "summary,outcome\n"
        "A contract dispute where the plaintiff presents strong evidence,plaintiff_wins\n"
        "The defendant wins on motion to dismiss for failure to state a claim,defendant_wins\n"
        "Jury verdict for plaintiff after negligence established,plaintiff_wins\n"
        "Defense prevails due to statute of limitations,defendant_wins\n"
    )

    rows = load_data(csv)
    model, vectorizer = train(rows)

    # Save to temp dir
    m = tmp_path / "model.pkl"
    v = tmp_path / "vectorizer.pkl"
    joblib.dump(model, m)
    joblib.dump(vectorizer, v)

    # Round-trip
    mdl = joblib.load(m)
    vec = joblib.load(v)

    X = vec.transform(["The plaintiff seeks damages for breach of contract."])
    proba = mdl.predict_proba(X)[0]
    assert proba.sum() == pytest.approx(1.0, rel=1e-6)
