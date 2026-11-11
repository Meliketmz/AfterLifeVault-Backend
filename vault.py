from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from database import Database


router = APIRouter(prefix="/api/vault-items", tags=["vault"])
database = Database()


class VaultItemCreate(BaseModel):
    owner_user_id: UUID
    title: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
    status: str = Field(default="active", min_length=1, max_length=30)

    @field_validator("title", "type", "content", "status")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Alan boş bırakılamaz.")
        return value


class VaultItemUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
    status: str = Field(min_length=1, max_length=30)

    @field_validator("title", "type", "content", "status")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Alan boş bırakılamaz.")
        return value


class VaultItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    title: str
    type: str
    content: str
    status: str


VAULT_ITEM_COLUMNS = """
    "Id" AS id,
    "OwnerUserId" AS owner_user_id,
    "Title" AS title,
    "Type" AS type,
    "Content" AS content,
    "Status" AS status
"""


def _ensure_owner_exists(owner_user_id: UUID) -> None:
    if database.fetch_one(
        'SELECT 1 FROM "USER" WHERE "Id" = %s',
        (owner_user_id,),
    ) is None:
        raise HTTPException(status_code=404, detail="Sahip kullanıcı bulunamadı.")


@router.post(
    "",
    response_model=VaultItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vault_item(payload: VaultItemCreate) -> dict:
    _ensure_owner_exists(payload.owner_user_id)
    item = database.execute_returning(
        f"""
        INSERT INTO "VAULT_ITEM"
            ("OwnerUserId", "Title", "Type", "Content", "Status")
        VALUES (%s, %s, %s, %s, %s)
        RETURNING {VAULT_ITEM_COLUMNS}
        """,
        (
            payload.owner_user_id,
            payload.title.strip(),
            payload.type.strip(),
            payload.content,
            payload.status.strip(),
        ),
    )
    if item is None:
        raise HTTPException(status_code=500, detail="Vault kaydı oluşturulamadı.")
    return item


@router.get("", response_model=list[VaultItemResponse])
def list_vault_items(
    owner_user_id: UUID = Query(..., description="Vault sahibinin kullanıcı ID'si"),
) -> list[dict]:
    return database.fetch_all(
        f"""
        SELECT {VAULT_ITEM_COLUMNS}
        FROM "VAULT_ITEM"
        WHERE "OwnerUserId" = %s
        ORDER BY "Id"
        """,
        (owner_user_id,),
    )


@router.get("/{item_id}", response_model=VaultItemResponse)
def get_vault_item(
    item_id: UUID,
    owner_user_id: UUID = Query(..., description="Vault sahibinin kullanıcı ID'si"),
) -> dict:
    item = database.fetch_one(
        f"""
        SELECT {VAULT_ITEM_COLUMNS}
        FROM "VAULT_ITEM"
        WHERE "Id" = %s AND "OwnerUserId" = %s
        """,
        (item_id, owner_user_id),
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Vault kaydı bulunamadı.")
    return item


@router.put("/{item_id}", response_model=VaultItemResponse)
def update_vault_item(
    item_id: UUID,
    payload: VaultItemUpdate,
    owner_user_id: UUID = Query(..., description="Vault sahibinin kullanıcı ID'si"),
) -> dict:
    item = database.execute_returning(
        f"""
        UPDATE "VAULT_ITEM"
        SET "Title" = %s, "Type" = %s, "Content" = %s, "Status" = %s
        WHERE "Id" = %s AND "OwnerUserId" = %s
        RETURNING {VAULT_ITEM_COLUMNS}
        """,
        (
            payload.title.strip(),
            payload.type.strip(),
            payload.content,
            payload.status.strip(),
            item_id,
            owner_user_id,
        ),
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Vault kaydı bulunamadı.")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vault_item(
    item_id: UUID,
    owner_user_id: UUID = Query(..., description="Vault sahibinin kullanıcı ID'si"),
) -> None:
    item = database.execute_returning(
        'DELETE FROM "VAULT_ITEM" '
        'WHERE "Id" = %s AND "OwnerUserId" = %s '
        'RETURNING "Id"',
        (item_id, owner_user_id),
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Vault kaydı bulunamadı.")
