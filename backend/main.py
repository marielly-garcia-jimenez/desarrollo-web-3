import os
import pytz
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
from pymongo import MongoClient
from prometheus_fastapi_instrumentator import Instrumentator 
from loki_logger_handler.loki_logger_handler import LokiLoggerHandler
import sys
import logging


# ============================================================
# LOGGER SETUP
# ============================================================

logger = logging.getLogger("custom_logger")
logging_data = os.getenv("LOG_LEVEL", "INFO").upper()

logger.setLevel(logging.DEBUG if logging_data == "DEBUG" else logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logger.level)

formatter = logging.Formatter(
    "%(levelname)s: %(asctime)s - %(name)s - %(message)s"
)
console_handler.setFormatter(formatter)

loki_handler = LokiLoggerHandler(
    url="http://loki:3100/loki/api/v1/push",
    labels={"application": "FastApi"},
    label_keys={},
    timeout=10,
)

logger.addHandler(loki_handler)
logger.addHandler(console_handler)

logger.info("Logger initialized")


# ============================================================
# FASTAPI + CORS
# ============================================================

app = FastAPI(
    title="Calculator API - Project",
    description="API para calculadora con historial en MongoDB, operaciones de N números y validaciones."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MONGO CONNECTION
# ============================================================

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27020")

try:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client.practica1
    collection_historial = db.historial

    logger.info("Conexión exitosa a MongoDB.")

except Exception as e:
    logger.error(f"Error de conexión a MongoDB: {e}")

    # ---------- Mock Cursor ----------
    class MockCursor:
        def __init__(self, data):
            self.data = data

        def sort(self, *args, **kwargs):
            logger.warning("Usando MockCursor.sort() debido a falla en Mongo")
            return self.data

    # ---------- Mock Collection ----------
    class MockCollection:
        def insert_one(self, doc):
            logger.warning("MockCollection.insert_one() - El documento NO se guardó (Mongo desconectado)")

        def find(self, query=None):
            logger.warning("MockCollection.find() - Devolviendo cursor vacío")
            return MockCursor([])

        def delete_many(self, query=None):
            logger.warning("MockCollection.delete_many() - No se eliminó nada (Mongo desconectado)")

    collection_historial = MockCollection()



# ============================================================
# DATA MODELS
# ============================================================

class OperationData(BaseModel):
    numbers: List[float] = Field(..., min_length=2)

class BatchOperation(BaseModel):
    operation: str
    numbers: List[float] = Field(..., min_length=2)



# ============================================================
# HELPERS
# ============================================================

def get_datetime():
    return datetime.now(pytz.timezone("America/Mexico_City"))


def validate_numbers(numbers: List[float], operation_name: str):
    if any(num < 0 for num in numbers):
        logger.error(f"ERROR: Números negativos en operación {operation_name} -> {numbers}")
        raise HTTPException(
            status_code=400,
            detail={"error": "Negative numbers are not allowed.", "operation": operation_name, "operands": numbers}
        )

    if operation_name == "division" and any(num == 0 for num in numbers[1:]):
        logger.error(f"ERROR: División por cero en números {numbers}")
        raise HTTPException(
            status_code=403,
            detail={"error": "Division by zero is not allowed.", "operation": operation_name, "operands": numbers}
        )


def save_to_history(operation: str, numbers: List[float], result: float):
    try:
        now = get_datetime()
        formatted_date = now.strftime("%d/%m/%Y %H:%M")

        doc = {
            "operation": operation,
            "numbers": numbers,
            "result": result,
            "date": now,
            "formatted_date": formatted_date
        }

        collection_historial.insert_one(doc)
        logger.info(f"Historial guardado OK: {operation} {numbers} = {result}")

    except Exception as e:
        logger.error(f"Error al guardar en historial: {e}")



# ============================================================
# ENDPOINTS
# ============================================================

@app.post("/calculator/sum")
def calculate_sum(data: OperationData = Body(...)):
    logger.info(f"Solicitud suma: {data.numbers}")
    validate_numbers(data.numbers, "sum")

    result = sum(data.numbers)
    save_to_history("sum", data.numbers, result)

    logger.info("Operación suma exitosa")
    return {"operation": "sum", "numbers": data.numbers, "result": result}



@app.post("/calculator/subtract")
def calculate_subtract(data: OperationData = Body(...)):
    logger.info(f"Solicitud resta: {data.numbers}")
    validate_numbers(data.numbers, "subtract")

    result = data.numbers[0]
    for num in data.numbers[1:]:
        result -= num

    save_to_history("subtract", data.numbers, result)
    logger.info("Operación resta exitosa")
    return {"operation": "subtract", "numbers": data.numbers, "result": result}



@app.post("/calculator/multiply")
def calculate_multiply(data: OperationData = Body(...)):
    logger.info(f"Solicitud multiplicación: {data.numbers}")
    validate_numbers(data.numbers, "multiplication")

    result = 1.0
    for num in data.numbers:
        result *= num

    save_to_history("multiplication", data.numbers, result)
    logger.info("Operación multiplicación exitosa")
    return {"operation": "multiplication", "numbers": data.numbers, "result": result}



@app.post("/calculator/divide")
def calculate_divide(data: OperationData = Body(...)):
    logger.info(f"Solicitud división: {data.numbers}")
    validate_numbers(data.numbers, "division")

    result = data.numbers[0]
    for num in data.numbers[1:]:
        result /= num

    save_to_history("division", data.numbers, result)
    logger.info("Operación división exitosa")
    return {"operation": "division", "numbers": data.numbers, "result": result}



@app.post("/calculator/batch")
def calculate_batch(operations: List[BatchOperation] = Body(...)):
    logger.info("Solicitud batch recibida")

    results = []
    op_map = {
        "sum": ("sum", calculate_sum),
        "subtract": ("subtract", calculate_subtract),
        "multiplication": ("multiplication", calculate_multiply),
        "division": ("division", calculate_divide),
        "sub": ("subtract", calculate_subtract),
        "mul": ("multiplication", calculate_multiply),
        "div": ("division", calculate_divide),
    }

    for op in operations:
        op_type = op.operation.lower()
        numbers = op.numbers

        if op_type not in op_map:
            logger.error(f"Operación inválida en batch: {op_type}")
            results.append({"op": op_type, "error": "Invalid operation type.", "operands": numbers})
            continue

        api_name, api_func = op_map[op_type]

        try:
            op_data = OperationData(numbers=numbers)
            result_doc = api_func(op_data)
            results.append({"op": api_name, "result": result_doc["result"], "numbers": numbers})

        except HTTPException as e:
            logger.error(f"Error HTTP en batch: {e.detail}")
            results.append({"op": api_name, "error": e.detail["error"], "operands": e.detail["operands"]})

        except Exception as e:
            logger.error(f"Error inesperado en batch: {e}")
            error_message = "At least 2 numbers are required." if "min_length" in str(e) else str(e)
            results.append({"op": api_name, "error": error_message, "operands": numbers})

    logger.info("Batch finalizado")
    return results



@app.get("/calculator/history")
def get_history(
    operation: str = Query(None),
    sort_by: str = Query("date"),
    sort_order: str = Query("desc")
):
    try:
        filter_query = {}
        valid_ops = ["sum", "subtract", "multiplication", "division"]

        if operation and operation.lower() in valid_ops:
            filter_query["operation"] = operation.lower()

        sort_direction = -1 if sort_order == "desc" else 1
        sort_field = "result" if sort_by == "result" else "date"

        ops = collection_historial.find(filter_query).sort([(sort_field, sort_direction)])

        history = []
        for operation_doc in ops:
            formatted_date = operation_doc.get("formatted_date", str(operation_doc.get("date", "N/A")))
            history.append({
                "numbers": operation_doc.get("numbers", []),
                "result": operation_doc.get("result", 0),
                "operation": operation_doc.get("operation", "unknown"),
                "date": formatted_date
            })

        logger.info("Historial consultado correctamente")
        return {"history": history}

    except Exception as e:
        logger.error(f"Error al obtener historial: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving history")


Instrumentator().instrument(app).expose(app)

