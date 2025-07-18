#!/bin/bash

echo "🚀 Iniciando MiaSalud Integration API..."

# Iniciar la aplicación API y los workers en paralelo
echo "🛠️ Iniciando API y workers en paralelo..."
gunicorn -c gunicorn.conf.py app.main:app &
python workers/campaign_processor.py &
python workers/contact_processor.py &
python workers/crm_processor.py &

# Esperar a que todos los procesos terminen
wait