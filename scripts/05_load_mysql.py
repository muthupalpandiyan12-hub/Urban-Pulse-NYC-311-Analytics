
from pathlib import Path
import os
import getpass
import re

import pandas as pd
import mysql.connector
from mysql.connector import Error


# ==========================================
# URBAN PULSE - MYSQL DATA IMPORT
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = BASE_DIR / "data" / "cleaned_data_mysql.csv"

BATCH_SIZE = 1000

DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB_USER = os.getenv("MYSQL_USER", "root")
DB_NAME = os.getenv("MYSQL_DATABASE", "urban_pulse")
DB_TABLE = "nyc_311_full"


def get_mysql_password():
    """Read password securely without hardcoding it."""

    password = os.getenv("MYSQL_PASSWORD")

    if password is None:
        password = getpass.getpass(
            "Enter MySQL password: "
        )

    return password


def connect_database(password):
    """Create a MySQL connection."""

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=password,
        database=DB_NAME,
        connection_timeout=15
    )


def validate_csv():
    """Check that the CSV file exists."""

    if not CSV_FILE.is_file():
        raise FileNotFoundError(
            f"CSV file not found: {CSV_FILE}"
        )

    print(f"CSV file found: {CSV_FILE}")


def validate_columns(cursor):
    """Ensure CSV columns match MySQL table columns."""

    columns = pd.read_csv(
        CSV_FILE,
        nrows=0
    ).columns.tolist()

    cursor.execute(
        f"SELECT * FROM `{DB_TABLE}` LIMIT 0"
    )

    mysql_columns = [
        col[0] for col in cursor.description
    ]

    if columns != mysql_columns:
        raise RuntimeError(
            "CSV and MySQL columns do not match.\n"
            f"CSV columns: {columns}\n"
            f"MySQL columns: {mysql_columns}"
        )

    if not all(
        re.fullmatch(r"[A-Za-z0-9_]+", col)
        for col in columns
    ):
        raise ValueError(
            "Invalid column name found in CSV."
        )

    print("CSV and MySQL columns validated.")

    return columns


def import_data(cursor, db, columns):
    """Import CSV records in batches."""

    column_sql = ", ".join(
        f"`{col}`" for col in columns
    )

    placeholders = ", ".join(
        ["%s"] * len(columns)
    )

    insert_sql = (
        f"INSERT INTO `{DB_TABLE}` "
        f"({column_sql}) "
        f"VALUES ({placeholders})"
    )

    total = 0

    for chunk in pd.read_csv(
        CSV_FILE,
        chunksize=BATCH_SIZE,
        dtype=str,
        keep_default_na=False
    ):

        rows = [
            tuple(
                None if value == "" else value
                for value in row
            )
            for row in chunk.itertuples(
                index=False,
                name=None
            )
        ]

        if not rows:
            continue

        try:
            cursor.executemany(
                insert_sql,
                rows
            )

            db.commit()

        except Error:
            db.rollback()
            raise

        total += len(rows)

        print(
            f"Imported: {total:,} records"
        )

    return total


def main():

    print("=" * 55)
    print("URBAN PULSE - MYSQL DATA IMPORT")
    print("=" * 55)

    db = None
    cursor = None

    try:
        validate_csv()

        password = get_mysql_password()

        print("Connecting to MySQL...")

        db = connect_database(password)

        cursor = db.cursor()

        print("MySQL connection successful!")

        cursor.execute(
            f"SELECT COUNT(*) FROM `{DB_TABLE}`"
        )

        existing = cursor.fetchone()[0]

        if existing != 0:
            raise RuntimeError(
                f"Import stopped: {DB_TABLE} "
                f"already contains {existing:,} records."
            )

        columns = validate_columns(cursor)

        print("Starting CSV import...")

        total = import_data(
            cursor,
            db,
            columns
        )

        cursor.execute(
            f"SELECT COUNT(*) FROM `{DB_TABLE}`"
        )

        final_count = cursor.fetchone()[0]

        print("=" * 55)

        print(
            f"CSV records processed: {total:,}"
        )

        print(
            f"MySQL records: {final_count:,}"
        )

        if final_count != total:
            raise RuntimeError(
                "Row count mismatch!"
            )

        print(
            "IMPORT COMPLETED SUCCESSFULLY!"
        )

    except (
        Error,
        RuntimeError,
        FileNotFoundError,
        ValueError
    ) as exc:

        print(f"ERROR: {exc}")

    finally:

        if cursor is not None:
            cursor.close()

        if db is not None and db.is_connected():
            db.close()

        print("Database connection closed.")


if __name__ == "__main__":
    main()
