from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import SessionLocal
from app.db import models
from app.api import deps
from app.schemas.advisor import AdvisorCreate, AdvisorUpdate, AdvisorInDB
from app.core.config import get_settings

router = APIRouter()

@router.get("/", response_model=List[AdvisorInDB], summary="Obtener todos los asesores")
def read_advisors(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    """
    Obtiene una lista paginada de todos los asesores.
    """
    advisors = db.query(models.Advisor).order_by(models.Advisor.id).offset(skip).limit(limit).all()
    return advisors

@router.get("/{advisor_id}", response_model=AdvisorInDB, summary="Obtener asesor por ID")
def read_advisor(advisor_id: int, db: Session = Depends(deps.get_db)):
    """
    Obtiene un asesor específico usando su ID.
    """
    advisor = db.query(models.Advisor).filter(models.Advisor.id == advisor_id).first()
    if advisor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asesor no encontrado")
    return advisor

@router.post("/", response_model=AdvisorInDB, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo asesor")
def create_advisor(advisor_data: AdvisorCreate, db: Session = Depends(deps.get_db)):
    """
    Crea un nuevo asesor con la información proporcionada.
    Valida que el 'email' sea único.
    """
    # Opcional: Verificar si el email ya existe para evitar duplicados
    existing_advisor = db.query(models.Advisor).filter(models.Advisor.email == advisor_data.email).first()
    if existing_advisor:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un asesor con el email '{advisor_data.email}'"
        )
    
    db_advisor = models.Advisor(**advisor_data.model_dump())
    db.add(db_advisor)
    db.commit()
    db.refresh(db_advisor)
    return db_advisor

@router.put("/{advisor_id}", response_model=AdvisorInDB, summary="Actualizar asesor por ID")
def update_advisor(advisor_id: int, advisor_update: AdvisorUpdate, db: Session = Depends(deps.get_db)):
    """
    Actualiza un asesor existente por su ID.
    Los campos no proporcionados en el cuerpo de la solicitud no serán modificados.
    """
    db_advisor = db.query(models.Advisor).filter(models.Advisor.id == advisor_id).first()
    if db_advisor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asesor no encontrado")

    update_data = advisor_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_advisor, key, value)
    
    db.add(db_advisor)
    db.commit()
    db.refresh(db_advisor)
    return db_advisor

@router.delete("/{advisor_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar asesor por ID")
def delete_advisor(advisor_id: int, api_key: str = Query(..., description="Debes ingresar el API_KEY para confirmar la eliminación"), db: Session = Depends(deps.get_db)):
    settings = get_settings()
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API_KEY inválido. No autorizado para eliminar.")
    db_advisor = db.query(models.Advisor).filter(models.Advisor.id == advisor_id).first()
    if db_advisor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asesor no encontrado")
    db.delete(db_advisor)
    db.commit()
    return {"message": "Asesor eliminado exitosamente"}