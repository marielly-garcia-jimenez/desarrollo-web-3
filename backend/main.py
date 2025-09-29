import datetime
from fastapi import FastAPI
from pymongo import MongoClient
from fastapi.middleware.cors import CORMiddleware
app = FastAPI()
# Mongo DB connection
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods={"*"},
    allow_
)

mongo_client = MongoClient("mongodb://admin_user:web3@practicas-mongo-1:27017/")
database = mongo_client.practica1
collection_historial = database.historial
@app.get("/calculadora/sum")
def sumar(a: float, b: float):
 """
 Suma dos números que vienen como parámetros de query (?a=...&b=...)
 Ejemplo: /calculadora/sum?a=5&b=10
 """
 resultado = a + b
 document = {
 "resultado": resultado,
 "a": a,
 "b": b,
 "date": datetime.datetime.now(tz=datetime.timezone.utc),
 }

 collection_historial.insert_one(document)

 return {"a": a, "b": b, "resultado": resultado}

 @app.get("/calculadora/sum")
def obtener_historial():
 operaciones = collection_historial.find({})
 historial = []
 for operacion in operaciones:
 historial.append({
 "a": operacion["a"],
 "b": operacion["b"],
 "resultado": operacion["resultado"],
 "date": operacion["date"].isoformat()
 })

 return {"historial": historial}
