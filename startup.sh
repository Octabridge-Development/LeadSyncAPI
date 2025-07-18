#!/bin/bash

echo "🚀 Iniciando MiaSalud Integration API..."

# Verificar Python
python --version

# Instalar dependencias si no existen
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Verificar que uvicorn esté instalado
echo "🔍 Verificando uvicorn..."
which uvicorn
uvicorn --version


# Iniciar los workers en background y guardar logs
echo "🛠️ Iniciando workers en background..."
python start_workers.py > worker.log 2>&1 &
WORKER_PID=$!

# Iniciar la aplicación API
echo "🌐 Iniciando servidor..."
exec uvicorn application:app --host 0.0.0.0 --port 8000