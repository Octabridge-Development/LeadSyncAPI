# Dockerfile para LeadSyncAPI (FastAPI + Gunicorn + Workers)
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los requerimientos e instálalos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente (app y workers)
COPY app ./app
COPY workers ./workers

# Instala dependencias adicionales si es necesario (por ejemplo, para workers)
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Expón el puerto que usará la API
EXPOSE 8000

# Copia y configura el script de arranque (simplificado)
COPY startup.sh .
RUN chmod +x startup.sh

# Comando de inicio: Inicia la API con Gunicorn y los workers en segundo plano
CMD ["./startup.sh"]