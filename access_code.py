from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from database import Database


router = APIRouter(prefix="/api/access-codes", tags=["access-codes"])
database = Database()


def _validate_expiration(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("expires_at timezone bilgisi içermelidir.")
    if value <= datetime.now(timezone.utc):
        raise ValueError("expires_at gelecekte olmalıdır.")
    return value


class AccessCodeCreate(BaseModel):
    recipient_id: UUID
    code_hash: str = Field(min_length=1, max_length=255)
    expires_at: datetime

    @field_validator("code_hash")
    @classmethod
    def validate_code_hash(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code_hash boş bırakılamaz.")
        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime) -> datetime:
        return _validate_expiration(value)


class AccessCodeUpdate(BaseModel):
    code_hash: str = Field(min_length=1, max_length=255)
    expires_at: datetime
    used: bool

    @field_validator("code_hash")
    @classmethod
    def validate_code_hash(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code_hash boş bırakılamaz.")
        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime) -> datetime:
        return _validate_expiration(value)


class AccessCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recipient_id: UUID
    expires_at: datetime
    used: bool


ACCESS_CODE_COLUMNS = """
    "Id" AS id,
    "RecipientId" AS recipient_id,
    "ExpiresAt" AS expires_at,
    "Used" AS used
"""


def _ensure_recipient_exists(recipient_id: UUID) -> None:
    if database.fetch_one(
        'SELECT 1 FROM "RECIPIENT" WHERE "Id" = %s',
        (recipient_id,),
    ) is None:
        raise HTTPException(status_code=404, detail="Alıcı bulunamadı.")


@router.post(
    "",
    response_model=AccessCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_access_code(payload: AccessCodeCreate) -> dict:
    _ensure_recipient_exists(payload.recipient_id)
    access_code = database.execute_returning(
        f"""
        INSERT INTO "ACCESS_CODE"
            ("RecipientId", "CodeHash", "ExpiresAt")
        VALUES (%s, %s, %s)
        RETURNING {ACCESS_CODE_COLUMNS}
        """,
        (
            payload.recipient_id,
            payload.code_hash.strip(),
            payload.expires_at,
        ),
    )
    if access_code is None:
        raise HTTPException(status_code=500, detail="Access code oluşturulamadı.")
    return access_code


@router.get("", response_model=list[AccessCodeResponse])
def list_access_codes(
    recipient_id: UUID = Query(..., description="Alıcının kullanıcı ID'si"),
) -> list[dict]:
    return database.fetch_all(
        f"""
        SELECT {ACCESS_CODE_COLUMNS}
        FROM "ACCESS_CODE"
        WHERE "RecipientId" = %s
        ORDER BY "ExpiresAt" DESC
        """,
        (recipient_id,),
    )


@router.get("/{access_code_id}", response_model=AccessCodeResponse)
def get_access_code(
    access_code_id: UUID,
    recipient_id: UUID = Query(..., description="Alıcının kullanıcı ID'si"),
) -> dict:
    access_code = database.fetch_one(
        f"""
        SELECT {ACCESS_CODE_COLUMNS}
        FROM "ACCESS_CODE"
        WHERE "Id" = %s AND "RecipientId" = %s
        """,
        (access_code_id, recipient_id),
    )
    if access_code is None:
        raise HTTPException(status_code=404, detail="Access code bulunamadı.")
    return access_code


@router.put("/{access_code_id}", response_model=AccessCodeResponse)
def update_access_code(
    access_code_id: UUID,
    payload: AccessCodeUpdate,
    recipient_id: UUID = Query(..., description="Alıcının kullanıcı ID'si"),
) -> dict:
    access_code = database.execute_returning(
        f"""
        UPDATE "ACCESS_CODE"
        SET "CodeHash" = %s, "ExpiresAt" = %s, "Used" = %s
        WHERE "Id" = %s AND "RecipientId" = %s
        RETURNING {ACCESS_CODE_COLUMNS}
        """,
        (
            payload.code_hash.strip(),
            payload.expires_at,
            payload.used,
            access_code_id,
            recipient_id,
        ),
    )
    if access_code is None:
        raise HTTPException(status_code=404, detail="Access code bulunamadı.")
    return access_code


@router.delete("/{access_code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_access_code(
    access_code_id: UUID,
    recipient_id: UUID = Query(..., description="Alıcının kullanıcı ID'si"),
) -> None:
    access_code = database.execute_returning(
        'DELETE FROM "ACCESS_CODE" '
        'WHERE "Id" = %s AND "RecipientId" = %s '
        'RETURNING "Id"',
        (access_code_id, recipient_id),
    )
    if access_code is None:
        raise HTTPException(status_code=404, detail="Access code bulunamadı.")
