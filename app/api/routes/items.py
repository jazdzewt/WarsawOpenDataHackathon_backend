from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.services.item_service import ItemService

router = APIRouter()


def get_item_service(db: Session = Depends(get_db)) -> ItemService:
    return ItemService(db)


@router.get("", response_model=list[ItemRead], summary="List items")
def list_items(service: ItemService = Depends(get_item_service)) -> list[ItemRead]:
    return service.list()


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED, summary="Create item")
def create_item(payload: ItemCreate, service: ItemService = Depends(get_item_service)) -> ItemRead:
    return service.create(payload)


@router.get("/{item_id}", response_model=ItemRead, summary="Get item")
def get_item(item_id: int, service: ItemService = Depends(get_item_service)) -> ItemRead:
    item = service.get(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=ItemRead, summary="Update item")
def update_item(
    item_id: int, payload: ItemUpdate, service: ItemService = Depends(get_item_service)
) -> ItemRead:
    item = service.update(item_id, payload)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete item")
def delete_item(item_id: int, service: ItemService = Depends(get_item_service)) -> None:
    if not service.delete(item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
