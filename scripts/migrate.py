from pathlib import Path
import sys

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import BASE_DIR, DATABASE_URL


def main() -> None:
    migration_dir = BASE_DIR / "db" / "migrations"
    migration_files = sorted(migration_dir.glob("*.sql"))

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            for migration_file in migration_files:
                print(f"executando {migration_file.relative_to(BASE_DIR)}")
                cursor.execute(migration_file.read_text())


if __name__ == "__main__":
    main()
