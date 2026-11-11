import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from typing import Any

from fastapi import APIRouter, HTTPException, status
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from database import Database
from mail import EmailSender


router = APIRouter(prefix="/api/auth/email-verification", tags=["authentication"])
database = Database()
load_dotenv()

CODE_LIFETIME = timedelta(minutes=1)
SEND_COOLDOWN = timedelta(minutes=1)
MAX_ATTEMPTS = 5


def _validate_email(value: str) -> str:
    email = value.strip().lower()
    _, address = parseaddr(email)
    if not address or "@" not in address or address.startswith("@") or address.endswith("@"):
        raise ValueError("Geçerli bir e-posta adresi girilmelidir.")
    return email


def _verification_secret() -> bytes:
    secret = os.getenv("EMAIL_VERIFICATION_SECRET")
    if not secret:
        raise RuntimeError("EMAIL_VERIFICATION_SECRET .env içinde tanımlanmalıdır.")
    return secret.encode()


def _hash_code(code: str) -> str:
    return hmac.new(
        _verification_secret(),
        code.encode(),
        hashlib.sha256,
    ).hexdigest()


class EmailVerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class EmailVerificationCode(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class EmailVerificationResponse(BaseModel):
    message: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _generic_response() -> EmailVerificationResponse:
    return EmailVerificationResponse(
        message="E-posta adresi kayıtlıysa doğrulama kodu gönderildi."
    )


@router.post(
    "/request",
    response_model=EmailVerificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_email_verification(
    payload: EmailVerificationRequest,
) -> EmailVerificationResponse:
    now = _utc_now()
    code = f"{secrets.randbelow(1_000_000):06d}"
    with database.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT "Id", "LastSentAt", "VerifiedAt"
                FROM "EMAIL_VERIFICATION"
                WHERE "Email" = %s
                FOR UPDATE
                """,
                (payload.email,),
            )
            verification: dict[str, Any] | None = cursor.fetchone()
            if verification is not None and verification["VerifiedAt"] is not None:
                return _generic_response()

            if (
                verification is not None
                and now - verification["LastSentAt"] < SEND_COOLDOWN
            ):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Yeni kod göndermek için bir dakika bekleyin.",
                )

            if verification is None:
                cursor.execute(
                    """
                    INSERT INTO "EMAIL_VERIFICATION"
                        ("Email", "CodeHash", "ExpiresAt", "Attempts", "LastSentAt")
                    VALUES (%s, %s, %s, 0, %s)
                    """,
                    (
                        payload.email,
                        _hash_code(code),
                        now + CODE_LIFETIME,
                        now,
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE "EMAIL_VERIFICATION"
                    SET "CodeHash" = %s,
                        "ExpiresAt" = %s,
                        "Attempts" = 0,
                        "LastSentAt" = %s,
                        "VerifiedAt" = NULL
                    WHERE "Id" = %s
                    """,
                    (
                        _hash_code(code),
                        now + CODE_LIFETIME,
                        now,
                        verification["Id"],
                    ),
                )

    EmailSender().send(
        recipients=payload.email,
        subject="E-posta doğrulama kodunuz",
        body=f"Doğrulama kodunuz: {code}\nBu kod 1 dakika geçerlidir.",
    )
    return _generic_response()


@router.post(
    "/confirm",
    response_model=EmailVerificationResponse,
)
def confirm_email_verification(
    payload: EmailVerificationCode,
) -> EmailVerificationResponse:
    now = _utc_now()
    verification_error = False
    with database.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT "Id", "CodeHash", "ExpiresAt", "Attempts", "VerifiedAt"
                FROM "EMAIL_VERIFICATION"
                WHERE "Email" = %s
                FOR UPDATE
                """,
                (payload.email,),
            )
            verification: dict[str, Any] | None = cursor.fetchone()
            if verification is None or verification["VerifiedAt"] is not None:
                verification_error = True
            else:
                expires_at = verification["ExpiresAt"]
                attempts = verification["Attempts"]
                code_hash = verification["CodeHash"]
                is_valid = (
                    bool(code_hash)
                    and bool(expires_at)
                    and now <= expires_at
                    and attempts < MAX_ATTEMPTS
                    and hmac.compare_digest(_hash_code(payload.code), code_hash)
                )

                if not is_valid:
                    cursor.execute(
                        """
                        UPDATE "EMAIL_VERIFICATION"
                        SET "Attempts" = LEAST("Attempts" + 1, %s)
                        WHERE "Id" = %s
                        """,
                        (MAX_ATTEMPTS, verification["Id"]),
                    )
                    verification_error = True
                else:
                    cursor.execute(
                        """
                        UPDATE "EMAIL_VERIFICATION"
                        SET "VerifiedAt" = %s,
                            "CodeHash" = '',
                            "ExpiresAt" = %s,
                            "Attempts" = 0
                        WHERE "Id" = %s
                        """,
                        (now, now, verification["Id"]),
                    )
                    cursor.execute(
                        """
                        UPDATE "USER"
                        SET "EmailVerified" = TRUE
                        WHERE lower("Email") = %s
                        """,
                        (payload.email,),
                    )

    if verification_error:
        raise HTTPException(status_code=400, detail="Kod geçersiz.")

    return EmailVerificationResponse(message="E-posta başarıyla doğrulandı.")
