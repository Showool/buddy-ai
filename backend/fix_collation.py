"""
Fix PostgreSQL collation version mismatch warning
"""
import psycopg2
import sys
from app.config import settings

def fix_collation_version():
    conn = psycopg2.connect(settings.POSTGRESQL_URL)
    cursor = conn.cursor()

    try:
        db_name = settings.POSTGRESQL_URL.split('/')[-1].split('?')[0]

        print(f"Refreshing collation version for database '{db_name}'...")

        cursor.execute(f'ALTER DATABASE "{db_name}" REFRESH COLLATION VERSION;')
        conn.commit()

        print("SUCCESS: Collation version refreshed")
        print("Please restart PostgreSQL service for changes to take effect")

    except Exception as e:
        print(f"FAILED: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    fix_collation_version()