# app/utils/idempotency.py
"""
Utilidad para garantizar idempotencia en el procesamiento de mensajes.
"""

def is_duplicate_event(event_id: str) -> bool:
    # TODO: Implementar lógica real (por ejemplo, usando Redis o base de datos)
    return False

def check_idempotency(event_data: dict) -> bool:
    """
    Verifica si un evento ya fue procesado anteriormente.
    Por ahora retorna False (no es duplicado).
    """
    # TODO: Implementar lógica real de idempotencia
    manychat_id = event_data.get('manychat_id', '')
    return is_duplicate_event(manychat_id)
# app/utils/idempotency.py
"""
Utilidad para garantizar idempotencia en el procesamiento de mensajes.
"""

def is_duplicate_event(event_id: str) -> bool:
    # TODO: Implementar lógica real (por ejemplo, usando Redis o base de datos)
    return False

def check_idempotency(event_data: dict) -> bool:
    """
    Verifica si un evento ya fue procesado anteriormente.
    Por ahora retorna False (no es duplicado).
    """
    # TODO: Implementar lógica real de idempotencia
    manychat_id = event_data.get('manychat_id', '')
    return is_duplicate_event(manychat_id)