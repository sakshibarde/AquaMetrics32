# export_sqlite.py
import sqlite3
import pandas as pd
import os

# Print where we are so you can see the path
print(f"Running from: {os.getcwd()}")

# Try both common locations
paths_to_try = [
    'database/water_quality.db',
    'backend/database/water_quality.db',
    '../database/water_quality.db',
]

db_path = None
for path in paths_to_try:
    if os.path.exists(path):
        db_path = path
        print(f"Found DB at: {path}")
        break

if db_path is None:
    print("❌ Could not find water_quality.db. Searched in:")
    for p in paths_to_try:
        print(f"   {p}")
else:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM water_records", conn)
    conn.close()
    print(f"✅ Found {len(df)} rows, {len(df.columns)} columns")
    df.to_csv('water_records_export.csv', index=False)
    print(f"✅ Saved to: {os.path.abspath('water_records_export.csv')}")