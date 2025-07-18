# Dockerfile para LeadSyncAPI (FastAPI + Gunicorn)
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los requerimientos e instálalos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código fuente
COPY . .

# Expón el puerto que usará la app
EXPOSE 8000

# Copia el script de arranque
COPY startup.sh .
RUN chmod +x startup.sh

# Comando de inicio: API + workers
CMD ["./startup.sh"]
