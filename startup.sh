#!/bin/bash

# Inicia la API con Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 &

# Inicia los workers en segundo plano
python /app/workers/crm_processor.py &
python /app/workers/contact_processor.py &
python /app/workers/campaign_processor.py &

# Mantén el contenedor activo
wait