from fastapi import APIRouter, HTTPException, status

from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.services.item_service import item_service

router = APIRouter()


@router.get("", response_model=list[ItemRead], summary="List items")
def list_items() -> list[ItemRead]:
    return item_service.list()


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED, summary="Create item")
def create_item(payload: ItemCreate) -> ItemRead:
    return item_service.create(payload)


@router.get("/{item_id}", response_model=ItemRead, summary="Get item")
def get_item(item_id: int) -> ItemRead:
    item = item_service.get(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=ItemRead, summary="Update item")
def update_item(item_id: int, payload: ItemUpdate) -> ItemRead:
    item = item_service.update(item_id, payload)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete item")
def delete_item(item_id: int) -> None:
    if not item_service.delete(item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
