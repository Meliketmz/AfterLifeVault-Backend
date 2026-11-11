from database import Database
from schema import create_schema


def main() -> None:
    database = Database()
    try:
        create_schema(database)
        print("Database schema is ready.")
    finally:
        database.close()


if __name__ == "__main__":
    main()
