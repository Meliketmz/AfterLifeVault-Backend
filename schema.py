from database import Database


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS "USER" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "Name" VARCHAR(150) NOT NULL,
    "Email" VARCHAR(320) NOT NULL UNIQUE,
    CONSTRAINT user_email_not_blank CHECK (btrim("Email") <> '')
);

CREATE TABLE IF NOT EXISTS "RECIPIENT" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "Name" VARCHAR(150) NOT NULL,
    "Email" VARCHAR(320) NOT NULL,
    CONSTRAINT recipient_email_not_blank CHECK (btrim("Email") <> '')
);

CREATE TABLE IF NOT EXISTS "VAULT_ITEM" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "OwnerUserId" UUID NOT NULL,
    "Title" VARCHAR(255) NOT NULL,
    "Type" VARCHAR(50) NOT NULL,
    "Content" TEXT NOT NULL,
    "Status" VARCHAR(30) NOT NULL DEFAULT 'active',
    CONSTRAINT vault_item_owner_fk
        FOREIGN KEY ("OwnerUserId") REFERENCES "USER" ("Id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "VAULT_RECIPIENT" (
    "VaultItemId" UUID NOT NULL,
    "RecipientId" UUID NOT NULL,
    PRIMARY KEY ("VaultItemId", "RecipientId"),
    CONSTRAINT vault_recipient_vault_item_fk
        FOREIGN KEY ("VaultItemId") REFERENCES "VAULT_ITEM" ("Id") ON DELETE CASCADE,
    CONSTRAINT vault_recipient_recipient_fk
        FOREIGN KEY ("RecipientId") REFERENCES "RECIPIENT" ("Id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "ACCESS_CODE" (
    "Id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "RecipientId" UUID NOT NULL,
    "CodeHash" TEXT NOT NULL,
    "ExpiresAt" TIMESTAMPTZ NOT NULL,
    "Used" BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT access_code_recipient_fk
        FOREIGN KEY ("RecipientId") REFERENCES "RECIPIENT" ("Id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS vault_item_owner_idx
    ON "VAULT_ITEM" ("OwnerUserId");

CREATE INDEX IF NOT EXISTS access_code_recipient_idx
    ON "ACCESS_CODE" ("RecipientId");

CREATE INDEX IF NOT EXISTS access_code_active_idx
    ON "ACCESS_CODE" ("RecipientId", "Used", "ExpiresAt");
"""


def create_schema(database: Database) -> None:
    """Create the application tables and indexes if they do not exist."""
    with database.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_SQL)
