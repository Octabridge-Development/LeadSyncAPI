# PowerShell script para Windows
# scripts/docker-setup.ps1

Write-Host "🐳 Configurando MiaSalud Integration API con Docker..." -ForegroundColor Blue

# Verificar si Docker está instalado y corriendo
Write-Host "📦 Verificando Docker..." -ForegroundColor Blue
try {
    $dockerVersion = docker --version
    $composeVersion = docker-compose --version
    Write-Host "✅ Docker verificado: $dockerVersion" -ForegroundColor Green
    Write-Host "✅ Docker Compose verificado: $composeVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker no está disponible. Asegúrate de que Docker Desktop esté corriendo." -ForegroundColor Red
    Write-Host "💡 Pasos:" -ForegroundColor Yellow
    Write-Host "  1. Abrir Docker Desktop" -ForegroundColor Yellow
    Write-Host "  2. Esperar a que inicie completamente" -ForegroundColor Yellow
    Write-Host "  3. Volver a ejecutar este script" -ForegroundColor Yellow
    exit 1
}

# Crear directorios necesarios
Write-Host "📦 Creando directorios necesarios..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path "docker" | Out-Null
New-Item -ItemType Directory -Force -Path "scripts" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
Write-Host "✅ Directorios creados" -ForegroundColor Green

# Verificar archivo .env
Write-Host "📦 Verificando archivo .env..." -ForegroundColor Blue
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ Archivo .env creado desde .env.example" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Archivo .env.example no encontrado. Creando .env básico..." -ForegroundColor Yellow
        @"
DEBUG=true
API_KEY=Miasaludnatural123**
API_V1_STR=/api/v1
DATABASE_URL=mssql+pyodbc://sa:MiaSalud123**@database:1433/miasaludnaturaldb?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstorageaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstorageaccount1;QueueEndpoint=http://azurite:10001/devstorageaccount1;
ODOO_URL=https://ironsolutionbd.odoo.com
ODOO_DB=ironsolutionbd
ODOO_USERNAME=sistemas@miasaludnatural.com
ODOO_PASSWORD=Mia123**
ODOO_RATE_LIMIT=1.0
USE_KEY_VAULT=false
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Write-Host "✅ Archivo .env básico creado" -ForegroundColor Green
    }
} else {
    Write-Host "✅ Archivo .env encontrado" -ForegroundColor Green
}

# Construir imágenes Docker
Write-Host "📦 Construyendo imágenes Docker..." -ForegroundColor Blue
Write-Host "⏳ Esto puede tomar varios minutos la primera vez..." -ForegroundColor Yellow
docker-compose build --no-cache
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Imágenes construidas exitosamente" -ForegroundColor Green
} else {
    Write-Host "❌ Error al construir imágenes. Revisa los logs arriba." -ForegroundColor Red
    exit 1
}

# Crear red si no existe
Write-Host "📦 Configurando red Docker..." -ForegroundColor Blue
docker network create miasalud_network 2>$null
Write-Host "✅ Red Docker configurada" -ForegroundColor Green

# Iniciar servicios de infraestructura
Write-Host "📦 Iniciando servicios de infraestructura..." -ForegroundColor Blue
docker-compose up -d database redis azurite
Write-Host "✅ Servicios de infraestructura iniciados" -ForegroundColor Green

# Esperar a que SQL Server esté listo
Write-Host "📦 Esperando a que SQL Server esté listo..." -ForegroundColor Blue
Write-Host "⏳ Esto puede tomar hasta 2 minutos en el primer inicio..." -ForegroundColor Yellow

$maxAttempts = 60
$attempt = 0
do {
    $attempt++
    Write-Host "." -NoNewline -ForegroundColor Yellow
    Start-Sleep -Seconds 2

    $result = docker-compose exec -T database /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "MiaSalud123**" -Q "SELECT 1" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ SQL Server está listo!" -ForegroundColor Green
        break
    }
} while ($attempt -lt $maxAttempts)

if ($attempt -eq $maxAttempts) {
    Write-Host ""
    Write-Host "❌ SQL Server no respondió en 2 minutos." -ForegroundColor Red
    Write-Host "🔍 Verifica los logs: docker-compose logs database" -ForegroundColor Yellow
    exit 1
}

# Configurar base de datos
Write-Host "📦 Configurando base de datos..." -ForegroundColor Blue
$sqlCommand = @'
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = ''miasaludnaturaldb'')
BEGIN
    CREATE DATABASE miasaludnaturaldb;
    PRINT ''Base de datos miasaludnaturaldb creada'';
END
ELSE
    PRINT ''Base de datos miasaludnaturaldb ya existe'';
'@

docker-compose exec -T database /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "MiaSalud123**" -Q $sqlCommand
Write-Host "✅ Base de datos configurada" -ForegroundColor Green

# Iniciar API
Write-Host "📦 Iniciando API..." -ForegroundColor Blue
docker-compose up -d api
Write-Host "✅ API iniciada" -ForegroundColor Green

# Esperar a que la API esté lista
Write-Host "📦 Esperando a que la API esté lista..." -ForegroundColor Blue
$maxAttempts = 30
$attempt = 0
do {
    $attempt++
    Write-Host "." -NoNewline -ForegroundColor Yellow
    Start-Sleep -Seconds 2

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host ""
            Write-Host "✅ API está respondiendo!" -ForegroundColor Green
            break
        }
    }
    catch {
        # Continuar intentando
    }
} while ($attempt -lt $maxAttempts)

if ($attempt -eq $maxAttempts) {
    Write-Host ""
    Write-Host "⚠️ API no respondió en 1 minuto. Verifica los logs: docker-compose logs api" -ForegroundColor Yellow
}

# Iniciar workers
Write-Host "📦 Iniciando workers..." -ForegroundColor Blue
docker-compose up -d workers
Write-Host "✅ Workers iniciados" -ForegroundColor Green

# Mostrar estado final
Write-Host "📦 Verificando estado de los servicios..." -ForegroundColor Blue
docker-compose ps

Write-Host ""
Write-Host "🚀 ¡Setup completado!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Servicios disponibles:" -ForegroundColor Blue
Write-Host "  • API: http://localhost:8000" -ForegroundColor White
Write-Host "  • Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • SQL Server: localhost:1433 (sa/MiaSalud123**)" -ForegroundColor White
Write-Host "  • Redis: localhost:6379" -ForegroundColor White
Write-Host "  • Azurite: localhost:10000-10002" -ForegroundColor White
Write-Host ""
Write-Host "📋 Comandos útiles:" -ForegroundColor Blue
Write-Host "  • Ver logs: docker-compose logs -f [service]" -ForegroundColor White
Write-Host "  • Parar servicios: docker-compose down" -ForegroundColor White
Write-Host "  • Restart: docker-compose restart [service]" -ForegroundColor White
Write-Host "  • Entrar al contenedor: docker-compose exec [service] bash" -ForegroundColor White
Write-Host ""
Write-Host "🧪 Para ejecutar tests:" -ForegroundColor Blue
Write-Host "  • .\scripts\docker-test.ps1" -ForegroundColor White