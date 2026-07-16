import sqlite3

from app.database.schema_loader import DATABASE_PATH


def inspect_database() -> None:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    try:
        tables = ["Patient", "Examination", "Laboratory"]

        for table_name in tables:
            count = cursor.execute(
                f'SELECT COUNT(*) AS total FROM "{table_name}"'
            ).fetchone()["total"]

            print(f"\n{'=' * 70}")
            print(f"TABLE: {table_name}")
            print(f"ROW COUNT: {count}")
            print(f"{'=' * 70}")

            rows = cursor.execute(
                f'SELECT * FROM "{table_name}" LIMIT 3'
            ).fetchall()

            for index, row in enumerate(rows, start=1):
                print(f"\nRow {index}:")
                for column_name in row.keys():
                    print(f"  {column_name}: {row[column_name]}")

        print(f"\n{'=' * 70}")
        print("ID RELATIONSHIP CHECK")
        print(f"{'=' * 70}")

        patient_exam_matches = cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM "Examination" AS e
            INNER JOIN "Patient" AS p
                ON e."ID" = p."ID"
            """
        ).fetchone()["total"]

        patient_lab_matches = cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM "Laboratory" AS l
            INNER JOIN "Patient" AS p
                ON l."ID" = p."ID"
            """
        ).fetchone()["total"]

        print(
            "Examination rows matching Patient by ID:",
            patient_exam_matches,
        )
        print(
            "Laboratory rows matching Patient by ID:",
            patient_lab_matches,
        )

    finally:
        connection.close()


if __name__ == "__main__":
    inspect_database()
