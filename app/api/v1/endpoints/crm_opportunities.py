# app/api/v1/endpoints/crm_opportunities.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.repositories import ContactRepository, ContactStateRepository
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Asume que tendrás un servicio de colas y un mapeo de stages.
# Reemplaza 'your_queue_service' con el nombre real de tu módulo de servicio de colas.
from app.services.queue_service import QueueService # <-- Importación corregida del servicio de colas
from app.schemas.crm_opportunity import CRMOpportunityEvent # <-- Esta importación es la del esquema que acabas de revisar

router = APIRouter()
