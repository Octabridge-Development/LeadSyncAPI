import requests
import json

# Configuración
BASE_URL = "http://localhost:8000"

print("🧪 Probando MiaSalud Integration API...")
print("-" * 50)

# 1. Probar endpoint raíz
print("\n1. Probando endpoint raíz (/)...")
try:
    response = requests.get(f"{BASE_URL}/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# 2. Probar documentación
print("\n2. Verificando endpoints de documentación...")
docs_endpoints = [
    ("/docs", "Swagger UI"),
    ("/redoc", "ReDoc"),
    ("/openapi.json", "OpenAPI Schema")
]

for endpoint, name in docs_endpoints:
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        print(f"   {name} ({endpoint}): {'✅ OK' if response.status_code == 200 else f'❌ Error {response.status_code}'}")
    except Exception as e:
        print(f"   {name} ({endpoint}): ❌ Error - {str(e)}")

# 3. Probar health check simple
print("\n3. Probando health check simple (/health)...")
try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# 4. Probar health check detallado (requiere API key)
print("\n4. Probando health check detallado (con API key)...")
headers = {"X-API-KEY": "Miasaludnatural123**"}
try:
    response = requests.get(f"{BASE_URL}/api/v1/reports/health", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Sistema: {data.get('status', 'unknown')}")
        print(f"   Base de datos: {data.get('dependencies', {}).get('database', {}).get('status', 'unknown')}")
        print(f"   Colas: {data.get('dependencies', {}).get('queues', {}).get('status', 'unknown')}")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

print("\n" + "-" * 50)
print("✅ Prueba completada!")
print("\nSi ves errores arriba, verifica:")
print("1. Que hayas guardado todos los cambios")
print("2. Que hayas reiniciado el servidor (Ctrl+C y volver a ejecutar uvicorn)")
print("3. Que hayas agregado la importación de datetime en queue_service.py")
print("4. Que hayas actualizado app/api/v1/__init__.py")