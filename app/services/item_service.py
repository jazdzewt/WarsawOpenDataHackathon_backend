from app.schemas.item import ItemCreate, ItemRead, ItemUpdate


class ItemService:
    """In-memory storage. Replace with a real repository/database layer."""

    def __init__(self) -> None:
        self._items: dict[int, ItemRead] = {}
        self._next_id = 1

    def list(self) -> list[ItemRead]:
        return list(self._items.values())

    def get(self, item_id: int) -> ItemRead | None:
        return self._items.get(item_id)

    def create(self, payload: ItemCreate) -> ItemRead:
        item = ItemRead(id=self._next_id, **payload.model_dump())
        self._items[item.id] = item
        self._next_id += 1
        return item

    def update(self, item_id: int, payload: ItemUpdate) -> ItemRead | None:
        item = self._items.get(item_id)
        if item is None:
            return None
        updated = item.model_copy(update=payload.model_dump(exclude_unset=True))
        self._items[item_id] = updated
        return updated

    def delete(self, item_id: int) -> bool:
        return self._items.pop(item_id, None) is not None


item_service = ItemService()
