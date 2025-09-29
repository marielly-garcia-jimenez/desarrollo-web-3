# Imagen base
FROM node:18
# Carpeta de trabajo
WORKDIR /app
# Copiar dependencias
COPY package*.json ./
# Instalar dependencias
RUN npm install
# Copiar el resto del código
COPY . .
# Exponer el puerto donde corre React
EXPOSE 3000
# Iniciar en modo desarrollo (con hot reload)
CMD ["npm", "start"]