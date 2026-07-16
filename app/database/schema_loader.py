import sqlite3
from pathlib import Path


DATABASE_PATH = Path(
    "data/minidev-complete/minidev/MINIDEV/"
    "dev_databases/thrombosis_prediction/"
    "thrombosis_prediction.sqlite"
)


def load_database_schema(database_path: Path = DATABASE_PATH) -> str:
    if not database_path.exists():
        raise FileNotFoundError(f"Database not found: {database_path}")

    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    try:
        tables = cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        schema_sections: list[str] = []

        for (table_name,) in tables:
            columns = cursor.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            column_lines: list[str] = []

            for column in columns:
                _, name, data_type, not_null, default_value, primary_key = column

                properties: list[str] = []

                if primary_key:
                    properties.append("PRIMARY KEY")

                if not_null:
                    properties.append("NOT NULL")

                if default_value is not None:
                    properties.append(f"DEFAULT {default_value}")

                property_text = (
                    f" [{', '.join(properties)}]"
                    if properties
                    else ""
                )

                column_lines.append(
                    f'  - "{name}" {data_type or "UNKNOWN"}{property_text}'
                )

            schema_sections.append(
                f'TABLE "{table_name}"\n' + "\n".join(column_lines)
            )

        return "\n\n".join(schema_sections)

    finally:
        connection.close()


if __name__ == "__main__":
    print(load_database_schema())
