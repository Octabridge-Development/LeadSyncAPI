#!/bin/bash
set -e

echo "🧪 Ejecutando tests en Docker..."

# Load environment variables
if [ -f docker/.env ]; then
    export $(cat docker/.env | grep -v '^#' | xargs)
fi

# Levantar servicios de test en background
docker-compose -f docker/docker-compose.test.yml --env-file docker/.env up -d

# Esperar a que la API esté lista (loop healthcheck)
echo "⏳ Esperando a que la API esté lista..."
for i in {1..20}; do
  if docker-compose -f docker/docker-compose.test.yml exec -T api curl -sf http://localhost:8000/health > /dev/null; then
    echo "API lista!"
    break
  fi
  sleep 2
done

# Ejecutar tests dentro del contenedor api
docker-compose -f docker/docker-compose.test.yml exec -T api pytest tests/ -v

# Health check (dentro del contenedor API)
echo "🏥 Verificando health check..."
docker-compose -f docker/docker-compose.test.yml exec -T api curl -f http://localhost:8000/health || exit 1

# Test de endpoints (dentro del contenedor API)
echo "📡 Probando endpoints..."
docker-compose -f docker/docker-compose.test.yml exec -T api curl -X POST "http://localhost:8000/api/v1/manychat/webhook/contact" \
    -H "Content-Type: application/json" \
    -H "X-API-KEY: ${API_KEY}" \
    -d '{"manychat_id": "test_docker", "nombre_lead": "Test Docker", "datetime_actual": "2024-05-01"}' \
    || exit 1

echo "✅ Todos los tests pasaron!"

# Limpiar
docker-compose -f docker/docker-compose.test.yml down -v