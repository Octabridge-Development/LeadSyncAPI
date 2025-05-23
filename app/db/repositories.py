from sqlalchemy.orm import Session

class BaseRepository:
    """
    Clase base para repositorios.
    Proporciona métodos CRUD genéricos.
    """
    def __init__(self, db: Session):
        self.db = db

    def get(self, model, id):
        return self.db.query(model).get(id)

    def create(self, model, obj_in):
        db_obj = model(**obj_in.dict())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj, obj_in):
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, model, id):
        obj = self.get(model, id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj