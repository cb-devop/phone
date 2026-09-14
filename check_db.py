import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("=" * 60)
print("📋 TABLE STRUCTURE")
print("=" * 60)

cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'phones'
    ORDER BY ordinal_position
""")
cols = cur.fetchall()
print(f"Total columns: {len(cols)}")
for c in cols:
    print(f"  • {c[0]} ({c[1]})")

print("\n" + "=" * 60)
print("📊 DATA COUNT")
print("=" * 60)

cur.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(brand) as brand,
        COUNT(model) as model,
        COUNT(price_inr) as price,
        COUNT(image_url) as image,
        COUNT(full_specs) as specs
    FROM phones
""")
row = cur.fetchone()
print(f"Total phones:     {row[0]}")
print(f"With brand:       {row[1]}")
print(f"With model:       {row[2]}")
print(f"With price:       {row[3]}")
print(f"With image:       {row[4]}")
print(f"With full_specs:  {row[5]}")

print("\n" + "=" * 60)
print("📱 PHONES DATA")
print("=" * 60)

cur.execute("""
    SELECT 
        id, brand, model, release_year, 
        price_inr, ram_gb, battery_mah, chipset,
        CASE WHEN image_url IS NOT NULL THEN '✅' ELSE '❌' END as img,
        reference_url
    FROM phones
    ORDER BY id
""")

for row in cur.fetchall():
    print(f"\nID: {row[0]}")
    print(f"  📱 {row[1]} {row[2]} ({row[3]})")
    print(f"  💰 ₹{row[4]} | RAM: {row[5]}GB | Battery: {row[6]}mAh")
    print(f"  ⚡ {row[7]}")
    print(f"  🖼️  Image: {row[8]}")
    print(f"  🔗 {row[9][:70]}...")

cur.close()
conn.close()
print("\n✅ Done")