from fastapi import Security, HTTPException, status, Request, Depends, Header
from fastapi.security.api_key import APIKeyHeader
from .config import get_settings
from fastapi_limiter.depends import RateLimiter
import ipaddress

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

# Lista de IPs bloqueadas (puede migrarse a Redis o BD en producción)
BLOCKED_IPS = set()

def get_api_key(api_key: str = Security(api_key_header)):
    settings = get_settings()
    if api_key == settings.API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )

# Dependencia para rate limiting y bloqueo de IPs
async def secure_request(request: Request, api_key: str = Depends(get_api_key),
                        limiter=Depends(RateLimiter(times=5, seconds=60))):
    client_ip = request.client.host
    try:
        ipaddress.ip_address(client_ip)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address")
    if client_ip in BLOCKED_IPS:
        raise HTTPException(status_code=403, detail="IP bloqueada")
    return True

async def verify_manychat_api_key(x_api_key: str = Header(None)):
    expected_key = get_settings().API_KEY  # Lee la API Key desde .env
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key