from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class ItemRead(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
