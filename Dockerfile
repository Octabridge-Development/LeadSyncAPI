# Dockerfile para LeadSyncAPI (FastAPI + Gunicorn + Workers)
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema necesarias para ODBC
RUN apt-get update && apt-get install -y \
    gnupg \
    curl \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get install -y unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia los requerimientos e instálalos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente (app y workers)
COPY app ./app
COPY workers ./workers

# Expón el puerto que usará la API
EXPOSE 8000

# Copia y configura el script de arranque
COPY startup.sh .
RUN chmod +x startup.sh

# Comando de inicio: Ejecuta startup.sh
CMD ["./startup.sh"]