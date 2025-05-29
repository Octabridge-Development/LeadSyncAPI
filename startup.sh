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

# Iniciar la aplicación
echo "🌐 Iniciando servidor..."
exec uvicorn application:app --host 0.0.0.0 --port 8000