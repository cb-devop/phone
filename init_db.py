"""
Database Initialization Script
Layerbase par schema create karta hai
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 60)
    print("🔧 Initializing Database on Layerbase")
    print("=" * 60)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        with open("schema.sql", "r", encoding="utf-8") as f:
            sql = f.read()

        cur.execute(sql)
        conn.commit()

        # Verify
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

        print("✅ Schema created successfully")
        print(f"📊 Tables: {', '.join(tables)}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()