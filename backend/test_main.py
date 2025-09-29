import mongomock
import pytest
from pystest import monkeypatch

from pymongo import MongoClient
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

import main


client = TestClient(app)
fake_mongo_client = mongomock.MongoClient()
database = mongo_client.practica1
collection_historial = database.historial

@pytest.mark.parametrize(
    "numeroA, numeroB, resultado",
    [
        (5, 10, 15),
        (0, 0, 0),
        (-5, 5, 0),
        (-10,-5, -15),
        (10, -20, -10)
    ]
)
def test_sumar(numeroA, numeroB, resultado):
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)
    response = client.get(f"/calculadora/suma?a{numeroA}&b={numeroB}")
    assert response.status_code ==200
    assert response.json() == {"a": numeroA, "b": numeroB, "resultado": resultado}

    assert collection_historial.find_one({"resultado": resultado, "a": numeroA. "b": numeroB})

def test_historial(monkeypatch):
    monkeypatch.setattr(main, "collection_historial", fake_collection_historial)

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

        print(f"DEBUG: expected_data: {historial}")
        print(f"DEBUG: response.json(): {response.json()}")