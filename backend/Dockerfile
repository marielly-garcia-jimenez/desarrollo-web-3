# Imagen base ligera de Python
FROM python:3.11-slim
# Crear directorio de trabajo
WORKDIR /app
# Copiar dependencias
COPY requirements.txt .
# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt
# Copiar el código de la aplicación
COPY . .
# Exponer el puerto donde correrá la app
EXPOSE 8000
# Comando para iniciar la API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]