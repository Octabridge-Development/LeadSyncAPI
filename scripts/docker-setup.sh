#!/bin/bash
set -e

echo "🐳 Configurando MiaSalud Integration API con Docker..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con colores
print_step() {
    echo -e "${BLUE}📦 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado. Instala Docker Desktop primero."
    exit 1
fi

# Verificar si Docker Compose está disponible
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose no está disponible. Instala Docker Compose."
    exit 1
fi

print_step "Verificando Docker..."
docker --version
docker-compose --version
print_success "Docker verificado correctamente"

# Crear directorios necesarios si no existen
print_step "Creando directorios necesarios..."
mkdir -p docker/postgres
mkdir -p scripts
mkdir -p logs
print_success "Directorios creados"

# Verificar archivo .env
if [ ! -f .env ]; then
    print_warning "Archivo .env no encontrado. Copiando desde .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success "Archivo .env creado desde .env.example"
    else
        print_error "Archivo .env.example no encontrado. Crea el archivo .env manualmente."
        exit 1
    fi
else
    print_success "Archivo .env encontrado"
fi

# Construir imágenes Docker
print_step "Construyendo imágenes Docker..."
docker-compose build --no-cache
print_success "Imágenes construidas exitosamente"

# Crear red si no existe
print_step "Configurando red Docker..."
docker network create miasalud_network 2>/dev/null || true
print_success "Red Docker configurada"

# Iniciar servicios de infraestructura primero
print_step "Iniciando servicios de infraestructura..."
docker-compose up -d database redis azurite
print_success "Servicios de infraestructura iniciados"

# Esperar a que la base de datos esté lista
print_step "Esperando a que SQL Server esté listo..."
echo "Esto puede tomar hasta 2 minutos en el primer inicio..."

# Loop para esperar a que SQL Server esté listo
for i in {1..60}; do
    if docker-compose exec -T database /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "MiaSalud123**" -Q "SELECT 1" &>/dev/null; then
        print_success "SQL Server está listo!"
        break
    fi
    echo -n "."
    sleep 2
done

if [ $i -eq 60 ]; then
    print_error "SQL Server no respondió en 2 minutos. Verifica los logs: docker-compose logs database"
    exit 1
fi

# Crear base de datos si no existe
print_step "Configurando base de datos..."
docker-compose exec -T database /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "MiaSalud123**" -Q "
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'miasaludnaturaldb')
BEGIN
    CREATE DATABASE miasaludnaturaldb;
    PRINT 'Base de datos miasaludnaturaldb creada';
END
ELSE
    PRINT 'Base de datos miasaludnaturaldb ya existe';
" || print_warning "Error al crear base de datos (puede que ya exista)"

# Iniciar API
print_step "Iniciando API..."
docker-compose up -d api
print_success "API iniciada"

# Esperar a que la API esté lista
print_step "Esperando a que la API esté lista..."
for i in {1..30}; do
    if curl -sf http://localhost:8000/health &>/dev/null; then
        print_success "API está respondiendo!"
        break
    fi
    echo -n "."
    sleep 2
done

if [ $i -eq 30 ]; then
    print_warning "API no respondió en 1 minuto. Verifica los logs: docker-compose logs api"
fi

# Iniciar workers
print_step "Iniciando workers..."
docker-compose up -d workers
print_success "Workers iniciados"

# Mostrar estado final
print_step "Verificando estado de los servicios..."
docker-compose ps

print_success "¡Setup completado!"
echo ""
echo "🚀 Servicios disponibles:"
echo "  • API: http://localhost:8000"
echo "  • Docs: http://localhost:8000/docs"
echo "  • SQL Server: localhost:1433 (sa/MiaSalud123**)"
echo "  • Redis: localhost:6379"
echo "  • Azurite: localhost:10000-10002"
echo ""
echo "📋 Comandos útiles:"
echo "  • Ver logs: docker-compose logs -f [service]"
echo "  • Parar servicios: docker-compose down"
echo "  • Restart: docker-compose restart [service]"
echo "  • Entrar al contenedor: docker-compose exec [service] bash"
echo ""
echo "🧪 Para ejecutar tests:"
echo "  • ./scripts/docker-test.sh"