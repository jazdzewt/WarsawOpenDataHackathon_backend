from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.item import Item
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate


class ItemService:
    """All queries go through the SQLAlchemy ORM, which binds every value as a
    parameter. User input is never concatenated into SQL, so it cannot inject SQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list(self) -> list[ItemRead]:
        items = self._db.scalars(select(Item).order_by(Item.id)).all()
        return [ItemRead.model_validate(item) for item in items]

    def get(self, item_id: int) -> ItemRead | None:
        item = self._db.get(Item, item_id)
        return ItemRead.model_validate(item) if item else None

    def create(self, payload: ItemCreate) -> ItemRead:
        item = Item(**payload.model_dump())
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return ItemRead.model_validate(item)

    def update(self, item_id: int, payload: ItemUpdate) -> ItemRead | None:
        item = self._db.get(Item, item_id)
        if item is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        self._db.commit()
        self._db.refresh(item)
        return ItemRead.model_validate(item)

    def delete(self, item_id: int) -> bool:
        item = self._db.get(Item, item_id)
        if item is None:
            return False
        self._db.delete(item)
        self._db.commit()
        return True
