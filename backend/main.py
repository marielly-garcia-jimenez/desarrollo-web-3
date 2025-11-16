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
from fastapi import FastAPI


logger = logging.getLogger("custom_logger")
logging_data = os.getenv("LOG_LEVEL", "INFO").upper()

if logging_data == "DEBUG":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)



# Create a console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logger.level)
formatter = logging.Formatter(
    "%(levelname)s: %(asctime)s - %(name)s - %(message)s"
)
console_handler.setFormatter(formatter)

# Create an instance of the custom handler
loki_handler = LokiLoggerHandler(
    url="http://loki:3100/loki/api/v1/push",
    labels={"application": "FastApi"},
    label_keys={},
    timeout=10,
)

logger.addHandler(loki_handler)
logger.addHandler(console_handler)
logger.info("Logger initialized")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MONGO_URL = os.environ.get(
    "MONGO_URL",
    "mongodb://localhost:27020"
)

try:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    db = client.practica1
    collection_historial = db.historial
    print("Conexión exitosa a MongoDB.")
except Exception as e:
    print(f"Error de conexión a MongoDB: {e}")

    class MockCursor:
        def __init__(self, data):
            self.data = data

        def sort(self, *args, **kwargs):
            # Devuelve una lista vacía simulando un cursor ordenado
            return self.data  

    class MockCollection:
        def insert_one(self, doc):
            pass

        def find(self, query=None):
            # Siempre devuelve una lista vacía a través del cursor mock
            return MockCursor([])

        def delete_many(self, query=None):
            pass

    collection_historial = MockCollection()



class OperationData(BaseModel):
    numbers: List[float] = Field(..., min_length=2, description="List of at least 2 numbers for the operation.")

class BatchOperation(BaseModel):
    operation: str = Field(..., description="Operation type (sum, subtract, multiply, divide).")
    numbers: List[float] = Field(..., min_length=2, description="List of at least 2 numbers for the operation.")



def get_datetime():
    return datetime.now(pytz.timezone('America/Mexico_City'))

def validate_numbers(numbers: List[float], operation_name: str):
    if any(num < 0 for num in numbers):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Negative numbers are not allowed.",
                "operation": operation_name,
                "operands": numbers
            }
        )
    if operation_name == "division":
        if any(num == 0 for num in numbers[1:]):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Division by zero is not allowed.",
                    "operation": operation_name,
                    "operands": numbers
                }
            )

def save_to_history(operation: str, numbers: List[float], result: float):
    try:
        now = get_datetime()
        formatted_date = now.strftime('%d/%m/%Y %H:%M')
        doc = {
            "operation": operation,
            "numbers": numbers,
            "result": result,
            "date": now,
            "formatted_date": formatted_date
        }
        collection_historial.insert_one(doc)
    except Exception as e:
        print(f"Error al guardar en historial: {e}")



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



@app.post("/calculator/sum")
def calculate_sum(data: OperationData = Body(...)):
    validate_numbers(data.numbers, "sum")
    result = sum(data.numbers)
    save_to_history("sum", data.numbers, result)

    logger.info(f"Operación suma exitoso")
    return {"operation": "sum", "numbers": data.numbers, "result": result}


@app.post("/calculator/subtract")
def calculate_subtract(data: OperationData = Body(...)):
    validate_numbers(data.numbers, "subtract")
    result = data.numbers[0]
    for num in data.numbers[1:]:
        result -= num
    save_to_history("subtract", data.numbers, result)
    return {"operation": "subtract", "numbers": data.numbers, "result": result}

@app.post("/calculator/multiply")
def calculate_multiply(data: OperationData = Body(...)):
    validate_numbers(data.numbers, "multiplication")
    result = 1.0
    for num in data.numbers:
        result *= num
    save_to_history("multiplication", data.numbers, result)
    
    logger.info(f"Operación suma exitoso")
    return {"operation": "multiplication", "numbers": data.numbers, "result": result}
     
    

@app.post("/calculator/divide")
def calculate_divide(data: OperationData = Body(...)):
    validate_numbers(data.numbers, "division")
    result = data.numbers[0]
    for num in data.numbers[1:]:
        result /= num
    save_to_history("division", data.numbers, result)
    return {"operation": "division", "numbers": data.numbers, "result": result}

@app.post("/calculator/batch")
def calculate_batch(operations: List[BatchOperation] = Body(...)):
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
            results.append({"op": op_type, "error": "Invalid operation type.", "operands": numbers})
            continue
        api_name, api_func = op_map[op_type]
        try:
            op_data = OperationData(numbers=numbers)
            result_doc = api_func(op_data)
            results.append({"op": api_name, "result": result_doc["result"], "numbers": numbers})
        except HTTPException as e:
            error_detail = e.detail
            results.append({"op": api_name, "error": error_detail["error"], "operands": error_detail["operands"]})
        except Exception as e:
            error_message = str(e)
            if "min_length" in error_message:
                error_message = "At least 2 numbers are required."
            results.append({"op": api_name, "error": error_message, "operands": numbers})
    return results

@app.get("/calculator/history")
def get_history(
    operation: str = Query(None, description="Filter by operation type"),
    sort_by: str = Query("date", description="Sort by field: date or result"),
    sort_order: str = Query("desc", description="Sort order: asc or desc")
):
    filter_query = {}
    valid_operations = ["sum", "subtract", "multiplication", "division"]
    if operation and operation.lower() in valid_operations:
        filter_query["operation"] = operation.lower()
    sort_direction = -1 if sort_order.lower() == "desc" else 1
    sort_field = "result" if sort_by.lower() == "result" else "date"
    operations = collection_historial.find(filter_query).sort([(sort_field, sort_direction)])
    history = []
    for operation_doc in operations:
        formatted_date = operation_doc.get("formatted_date", str(operation_doc.get("date", "N/A")))
        history.append({
            "numbers": operation_doc.get("numbers", []),
            "result": operation_doc.get("result", 0),
            "operation": operation_doc.get("operation", "unknown"),
            "date": formatted_date
        })
    return {"history": history}

    Instrumentator() .instrument(app) .expose(app)

