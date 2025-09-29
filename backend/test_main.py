import pytest
import mongomock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pytest import monkeypatch

from main import app
fake_mongo_client = mongomock.MongoClient()
fake_database = fake_mongo_client.practica1
fake_collection_historial = fake_database.historial

client = TestClient(app)


@pytest.mark.parametrize(
        "numeroa, numerob, resultado",
        [
            (5, 10, 15),
            (0, 0, 0),
            (-5, 5, 0),
            (-10, -5, -15),
            (2.5, 2.5, 5.0),
            (10, -20, -10)
        ]
)

def test_sumar(numeroa, numerob, resultado):
    monkeypatch.setattr(main,"collection_historia", fake_collection_historial)
    response = client.get(f"/calculadora/sum?a={numeroa}&b={numerob}")
    assert response.status_code == 200
    assert response.json() == {"a": numeroa, "b": numerob, "resultado": resultado}
    assert collection_historial.insert_one.called


def test_historial(monkeypatch): 
    monkeypatch.setattr(main, "collection_historia", fake_collection_historial)
    response = client.get("/calculadora/historial")
    assert response.status_code == 200

    
    expected_data = list(fake_collection_historial.find({}))

    historial = []
    for document in expected_data:
        historial.append({
            "a": document["a"],
            "b": document["b"],
            "resultado": document["resultado"],
            "date": document["date"].isoformat()
        })
    
    print(f"DEBUG: expected_date: {historial}")
    print(f"DEBUG: response.json(): {response.json()}")

    
    assert response.json() == {"historia": historial}