import pytest
import mongomock
from fastapi.testclient import TestClient
from datetime import datetime
import json
import main

# ==================== TEST SETUP ====================

client = TestClient(main.app)

# Crear un cliente mock de MongoDB y sobrescribir el cliente real en main.py
fake_mongo_client = mongomock.MongoClient()
database = fake_mongo_client.practica1
collection_historial = database.collection_historial

# Configuración del mock antes de cada prueba
@pytest.fixture(autouse=True)
def setup_teardown(monkeypatch):
    """Garantiza que el mock se use en main y limpia la colección antes de cada prueba."""
    monkeypatch.setattr(main, "collection_historial", collection_historial)
    collection_historial.delete_many({})
    # Mocks para asegurar que las fechas sean estables y usar la zona horaria de MX
    mexico_tz = main.pytz.timezone('America/Mexico_City')
    fixed_time = datetime(2025, 10, 2, 10, 30, 0, 0, tzinfo=mexico_tz)
    monkeypatch.setattr(main, "get_datetime", lambda: fixed_time)
    yield
    collection_historial.delete_many({}) # Limpiar después

# ==================== AUXILIARES ====================

def post_operation(endpoint, numbers):
    """Auxiliar para ejecutar peticiones POST con body JSON."""
    return client.post(
        f"/calculator/{endpoint}",
        json={"numbers": numbers}
    )

# ==================== PRUEBAS DE OPERACIONES (N NÚMEROS Y POST) ====================

@pytest.mark.parametrize(
    "numbers, expected_result",
    [
        ([10, 5, 5], 20),
        ([1.5, 2.5, 3.0, 3.0], 10.0),
    ]
)
def test_sum_n_numbers(numbers, expected_result):
    response = post_operation("sum", numbers)
    assert response.status_code == 200
    assert abs(response.json()["result"] - expected_result) < 0.01

@pytest.mark.parametrize(
    "numbers, expected_result",
    [
        ([10, 3, 2, 1], 4), # 10 - 3 - 2 - 1 = 4
        ([100, 20, 30], 50),
    ]
)
def test_subtract_n_numbers(numbers, expected_result):
    response = post_operation("subtract", numbers)
    assert response.status_code == 200
    assert abs(response.json()["result"] - expected_result) < 0.01

@pytest.mark.parametrize(
    "numbers, expected_result",
    [
        ([2, 3, 4, 1], 24), # 2 * 3 * 4 * 1 = 24
        ([5, 2.5, 2], 25.0),
    ]
)
def test_multiply_n_numbers(numbers, expected_result):
    response = post_operation("multiply", numbers)
    assert response.status_code == 200
    assert abs(response.json()["result"] - expected_result) < 0.01

@pytest.mark.parametrize(
    "numbers, expected_result",
    [
        ([100, 2, 5], 10.0), # 100 / 2 / 5 = 10
        ([120, 3, 4, 2], 5.0), 
    ]
)
def test_divide_n_numbers(numbers, expected_result):
    response = post_operation("divide", numbers)
    assert response.status_code == 200
    assert abs(response.json()["result"] - expected_result) < 0.01

# ==================== PRUEBAS DE VALIDACIÓN ====================

def test_divide_by_zero_error():
    """Test para división entre cero (Status 403)."""
    response = post_operation("divide", [10, 2, 0, 5])
    assert response.status_code == 403
    assert "Division by zero is not allowed" in response.json()["detail"]["error"]

def test_negative_numbers_error():
    """Test para números negativos (Status 400)."""
    response = post_operation("multiply", [5, -3, 2])
    assert response.status_code == 400
    assert "Negative numbers are not allowed" in response.json()["detail"]["error"]
    assert response.json()["detail"]["operation"] == "multiplication"

def test_insufficient_numbers_error():
    """Test para menos de 2 números (Error Pydantic 422)."""
    response = post_operation("sum", [5])
    assert response.status_code == 422 
    
# ==================== PRUEBAS DE OPERACIONES POR LOTE ====================

def test_batch_operations_success_and_error():
    """Tests para lote con operaciones exitosas y errores controlados."""
    batch_request = [
        {"operation": "sum", "numbers": [1, 2, 3]},       # 6 (Success)
        {"operation": "div", "numbers": [100, 0, 5]},      # Division by zero (Error 403)
        {"operation": "mul", "numbers": [2, 4]},           # 8 (Success)
        {"operation": "sub", "numbers": [5, -3]},          # Negative error (Error 400)
    ]
    
    response = client.post("/calculator/batch", json=batch_request)
    
    assert response.status_code == 200 
    results = response.json()
    
    assert len(results) == 4
    
    # 1. Suma Exitosa
    assert results[0]["op"] == "sum"
    assert results[0]["result"] == 6

    # 2. Error de División por Cero
    assert results[1]["op"] == "division"
    assert "Division by zero" in results[1]["error"]

    # 3. Multiplicación Exitosa
    assert results[2]["op"] == "multiplication"
    assert results[2]["result"] == 8

    # 4. Error de Número Negativo
    assert results[3]["op"] == "subtract"
    assert "Negative numbers are not allowed" in results[3]["error"]

def test_batch_history_tracking():
    """Tests que solo las operaciones exitosas en lote se guardan en historial, independientemente del orden."""
    batch_request = [
        {"operation": "sum", "numbers": [1, 1]},        # Success
        {"operation": "div", "numbers": [5, 0]},        # Error (No se guarda)
        {"operation": "mul", "numbers": [2, 5]},        # Success
    ]
    
    client.post("/calculator/batch", json=batch_request)
    
    history = client.get("/calculator/history").json()["history"]
    
    # 1. Verificar que solo se guardaron las 2 operaciones exitosas
    assert len(history) == 2
    
    # 2. Verificar que las operaciones correctas estén presentes (ignorando el orden)
    operations_found = [item["operation"] for item in history]
    assert "sum" in operations_found
    assert "multiplication" in operations_found

# ==================== PRUEBAS DE HISTORIAL AVANZADO ====================

@pytest.fixture
def populated_history(setup_teardown):
    """Fixture para poblar el historial mock con datos diversos para probar filtros y ordenamiento."""
    
    # Las fechas son cruciales para el orden: 10:00 (result 10), 11:00 (result 20), 12:00 (result 5), 09:00 del día siguiente (result 100)
    mexico_tz = main.pytz.timezone('America/Mexico_City')
    data = [
        {"operation": "sum", "numbers": [1, 9], "result": 10, "date": datetime(2025, 10, 2, 10, 0, tzinfo=mexico_tz)}, 
        {"operation": "divide", "numbers": [10, 2], "result": 5, "date": datetime(2025, 10, 2, 12, 0, tzinfo=mexico_tz)}, 
        {"operation": "sum", "numbers": [10, 10], "result": 20, "date": datetime(2025, 10, 2, 11, 0, tzinfo=mexico_tz)}, 
        {"operation": "multiplication", "numbers": [10, 10], "result": 100, "date": datetime(2025, 10, 3, 9, 0, tzinfo=mexico_tz)}, 
    ]
    # Simular el guardado en la base de datos real (incluyendo el campo 'date' para el sort)
    for doc in data:
        doc["formatted_date"] = doc["date"].strftime('%d/%m/%Y %H:%M')
    collection_historial.insert_many(data)
    
    return collection_historial

def test_history_filter_and_sort(populated_history):
    """Test para filtrar por tipo de operación y ordenar por resultado descendente."""
    # Filtrar por "sum" y ordenar por "result" descendente
    response = client.get("/calculator/history?operation=sum&sort_by=result&sort_order=desc")
    history = response.json()["history"]
    
    assert response.status_code == 200
    assert len(history) == 2
    assert history[0]["result"] == 20 # Mayor resultado de la suma
    assert history[1]["result"] == 10
    assert all(item["operation"] == "sum" for item in history)
    
def test_history_sort_by_date_asc(populated_history):
    """Test para ordenar por fecha ascendente (el más antiguo primero)."""
    response = client.get("/calculator/history?sort_by=date&sort_order=asc")
    history = response.json()["history"]
    
    assert response.status_code == 200
    # Orden por fecha: 10:00, 11:00, 12:00 (Oct 2), 09:00 (Oct 3)
    assert history[0]["result"] == 10
    assert history[1]["result"] == 20
    assert history[2]["result"] == 5
    assert history[3]["result"] == 100