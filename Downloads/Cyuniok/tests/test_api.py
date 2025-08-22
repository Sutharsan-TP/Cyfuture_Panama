import json
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_ok():
    r = client.get('/')
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'


def test_predict_validation():
    r = client.post('/predict', json={'summary': ''})
    assert r.status_code == 400


def test_predict_happy_path():
    payload = { 'summary': 'The plaintiff alleges breach of contract after delivery failure.' }
    r = client.post('/predict', json=payload)
    assert r.status_code == 200
    data = r.json()
    assert 'prediction' in data and 'confidence' in data
    assert isinstance(data['prediction'], str)
    assert 0.0 <= float(data['confidence']) <= 1.0
