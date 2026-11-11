import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from dotenv import load_dotenv
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class Database:
    """Manage a pool of connections to the remote PostgreSQL database."""

    def __init__(
        self,
        dsn: str | None = None,
        *,
        min_size: int = 1,
        max_size: int = 5,
    ) -> None:
        load_dotenv()
        self._dsn = dsn or os.getenv("DATABASE_URL_POOLED") or os.getenv("DATABASE_URL")
        if not self._dsn:
            raise RuntimeError(
                "Database connection string is missing. "
                "Set DATABASE_URL_POOLED or DATABASE_URL in .env."
            )
        if min_size < 1 or max_size < min_size:
            raise ValueError("Pool sizes must satisfy 1 <= min_size <= max_size.")

        self._pool = ConnectionPool(
            conninfo=self._dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=False,
        )

    def open(self) -> None:
        """Open the pool and wait until the initial connections are ready."""
        self._pool.open(wait=True)

    def close(self) -> None:
        """Close all connections in the pool."""
        self._pool.close()

    @contextmanager
    def connection(self) -> Iterator[Connection[Any]]:
        """Borrow a connection and return it to the pool after use."""
        if self._pool.closed:
            self.open()
        with self._pool.connection() as connection:
            yield connection

    def fetch_all(
        self,
        query: str,
        params: Sequence[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run a SELECT query and return rows as dictionaries."""
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

    def fetch_one(
        self,
        query: str,
        params: Sequence[Any] | None = None,
    ) -> dict[str, Any] | None:
        """Run a SELECT query and return the first row, if one exists."""
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()

    def execute_returning(
        self,
        query: str,
        params: Sequence[Any] | None = None,
    ) -> dict[str, Any] | None:
        """Run a write query with RETURNING and return the affected row."""
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()

    def execute(self, query: str, params: Sequence[Any] | None = None) -> None:
        """Run an INSERT, UPDATE, or DELETE query."""
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
