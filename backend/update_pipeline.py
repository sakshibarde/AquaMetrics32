# # backend/update_pipeline.py
# import pandas as pd
# import numpy as np
# import json
# import os
# from datetime import datetime

# # Import the db helper — works for both SQLite and Supabase
# from db import DATABASE_URL, get_connection, get_upsert_sql, execute_many

# try:
#     from models.preprocess import clean_and_fill
#     PREPROCESS_AVAILABLE = True
# except ImportError:
#     print("Warning: 'models.preprocess.clean_and_fill' not found. Basic cleaning will be applied.")
#     PREPROCESS_AVAILABLE = False

#     def clean_and_fill(df):
#         print("Applying basic cleaning...")
#         if 'timestamp' not in df.columns:
#             print("ERROR: 'timestamp' column missing.")
#             return pd.DataFrame()
#         try:
#             df['timestampDate'] = pd.to_datetime(df['timestamp'], errors='coerce')
#         except Exception as e:
#             print(f"ERROR converting 'timestamp': {e}")
#             df['timestampDate'] = pd.NaT

#         df = df.dropna(subset=['stationId', 'timestampDate'])
#         if df.empty:
#             return df

#         meta_cols = ['stationId', 'stationName', 'location', 'timestamp', 'timestampDate', 'id']
#         param_cols = [col for col in df.columns if col not in meta_cols]
#         for col in param_cols:
#             df[col] = pd.to_numeric(df[col], errors='coerce')
#         return df


# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# TABLE_NAME = "water_records"
# SCRAPED_DATA_JSON = os.path.join(SCRIPT_DIR, "static/scraped_data/latest_cpcb_data.json")


# def create_table_if_not_exists(param_cols, df_to_store):
#     """Creates the water_records table if it doesn't already exist."""
#     if DATABASE_URL:
#         # PostgreSQL syntax
#         cols_sql_parts = []
#         for col in param_cols:
#             if pd.api.types.is_float_dtype(df_to_store[col]):
#                 col_type = "DOUBLE PRECISION"
#             elif pd.api.types.is_integer_dtype(df_to_store[col]):
#                 col_type = "BIGINT"
#             else:
#                 col_type = "TEXT"
#             cols_sql_parts.append(f'"{col}" {col_type}')
#         cols_sql = ", ".join(cols_sql_parts)

#         create_sql = f"""
#         CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
#             "stationId" TEXT,
#             "timestampDate" TIMESTAMP,
#             "timestamp" TEXT,
#             {cols_sql},
#             PRIMARY KEY ("stationId", "timestampDate")
#         );
#         """
#     else:
#         # SQLite syntax
#         cols_sql_parts = []
#         for col in param_cols:
#             if pd.api.types.is_float_dtype(df_to_store[col]):
#                 col_type = "REAL"
#             elif pd.api.types.is_integer_dtype(df_to_store[col]):
#                 col_type = "INTEGER"
#             else:
#                 col_type = "TEXT"
#             cols_sql_parts.append(f'"{col}" {col_type}')
#         cols_sql = ", ".join(cols_sql_parts)

#         create_sql = f"""
#         CREATE TABLE IF NOT EXISTS "water_records" (
#             "stationId" TEXT,
#             "timestampDate" TIMESTAMP,
#             "timestamp" TEXT,
#             {cols_sql},
#             PRIMARY KEY ("stationId", "timestampDate")
#         );
#         """

#     conn = get_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(create_sql)
#         conn.commit()
#     finally:
#         conn.close()


# def preprocess_and_store_data():
#     print(f"[{datetime.now()}] --- Starting Database Update Pipeline ---")
#     print(f"Using: {'Supabase (PostgreSQL)' if DATABASE_URL else 'Local SQLite'}")

#     # 1. Read JSON scraped data
#     print(f"Reading scraped data from: {SCRAPED_DATA_JSON}")
#     if not os.path.exists(SCRAPED_DATA_JSON):
#         print(f"ERROR: Scraped data file not found at {SCRAPED_DATA_JSON}.")
#         return

#     try:
#         df = pd.read_json(SCRAPED_DATA_JSON, orient='records')
#         if df.empty:
#             print("Scraped data file is empty. No data to update.")
#             return
#         print(f"Loaded {len(df)} records from JSON.")
#     except Exception as e:
#         print(f"ERROR: Failed to read JSON file: {e}")
#         return

#     # 2. Clean data
#     print("Cleaning and preparing data...")
#     processed_df = clean_and_fill(df.copy())

#     if processed_df.empty:
#         print("No valid data remaining after cleaning. Skipping database update.")
#         return

#     if 'stationId' not in processed_df.columns:
#         print("ERROR: 'stationId' column missing after cleaning.")
#         return
#     if 'timestampDate' not in processed_df.columns or processed_df['timestampDate'].isnull().all():
#         print("ERROR: 'timestampDate' column missing or invalid after cleaning.")
#         return

#     # 3. Prepare for DB insertion
#     meta_cols = ['stationId', 'stationName', 'location', 'timestamp', 'timestampDate', 'id']
#     param_cols = sorted([col for col in processed_df.columns if col not in meta_cols])
#     db_cols = ['stationId', 'timestamp', 'timestampDate'] + param_cols
#     df_to_store = processed_df[[col for col in db_cols if col in processed_df.columns]].copy()

#     # Replace NaN with None for DB compatibility
#     df_to_store = df_to_store.replace({pd.NA: None, np.nan: None})

#     # Convert datetime columns to strings
#     if pd.api.types.is_datetime64_any_dtype(df_to_store['timestampDate']):
#         df_to_store['timestampDate'] = df_to_store['timestampDate'].dt.strftime('%Y-%m-%dT%H:%M:%S')
#     if 'timestamp' in df_to_store.columns and pd.api.types.is_datetime64_any_dtype(df_to_store['timestamp']):
#         df_to_store['timestamp'] = df_to_store['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

#     # 4. Create table and insert
#     print(f"Preparing to insert {len(df_to_store)} records into '{TABLE_NAME}'...")
#     try:
#         create_table_if_not_exists(param_cols, df_to_store)
#         sql = get_upsert_sql(TABLE_NAME, list(df_to_store.columns))
#         data_tuples = [tuple(None if (isinstance(x, float) and np.isnan(x)) else x for x in row)
#                        for row in df_to_store.to_numpy()]
#         execute_many(sql, data_tuples)
#     except Exception as e:
#         print(f"ERROR: Failed to store data: {e}")
#         import traceback
#         traceback.print_exc()

#     print(f"[{datetime.now()}] --- Database Update Pipeline Finished ---")


# if __name__ == "__main__":
#     preprocess_and_store_data()


# backend/update_pipeline.py
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

from db import DATABASE_URL, get_connection

try:
    from models.preprocess import clean_and_fill
except ImportError:
    def clean_and_fill(df):
        if 'timestamp' not in df.columns:
            return pd.DataFrame()
        df['timestampDate'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestampDate'])
        meta = ['stationId','stationName','location','timestamp','timestampDate','id']
        for col in [c for c in df.columns if c not in meta]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

SCRIPT_DIR        = os.path.dirname(os.path.abspath(__file__))
TABLE_NAME        = "water_records"
SCRAPED_DATA_JSON = os.path.join(SCRIPT_DIR, "static/scraped_data/latest_cpcb_data.json")


def preprocess_and_store_data():
    print(f"[{datetime.now()}] --- Starting Database Update Pipeline ---")
    print(f"Using: {'Supabase (PostgreSQL)' if DATABASE_URL else 'Local SQLite'}")

    if not os.path.exists(SCRAPED_DATA_JSON):
        print(f"ERROR: {SCRAPED_DATA_JSON} not found.")
        return

    try:
        df = pd.read_json(SCRAPED_DATA_JSON, orient='records')
        if df.empty:
            print("Scraped data file is empty.")
            return
        print(f"Loaded {len(df)} records from JSON.")
    except Exception as e:
        print(f"ERROR reading JSON: {e}")
        return

    processed_df = clean_and_fill(df.copy())
    if processed_df.empty:
        print("No valid data after cleaning.")
        return

    if 'stationId' not in processed_df.columns:
        print("ERROR: stationId missing.")
        return
    if 'timestampDate' not in processed_df.columns or processed_df['timestampDate'].isnull().all():
        print("ERROR: timestampDate missing.")
        return

    meta_cols = ['stationId','stationName','location','timestamp','timestampDate','id']
    param_cols = sorted([c for c in processed_df.columns if c not in meta_cols])
    db_cols = ['stationId','timestamp','timestampDate'] + param_cols
    df_to_store = processed_df[[c for c in db_cols if c in processed_df.columns]].copy()
    df_to_store = df_to_store.replace({pd.NA: None, np.nan: None})

    if pd.api.types.is_datetime64_any_dtype(df_to_store.get('timestampDate', pd.Series())):
        df_to_store['timestampDate'] = df_to_store['timestampDate'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    if 'timestamp' in df_to_store.columns and pd.api.types.is_datetime64_any_dtype(df_to_store['timestamp']):
        df_to_store['timestamp'] = df_to_store['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

    print(f"Inserting {len(df_to_store)} records into '{TABLE_NAME}'...")
    conn = get_connection()
    try:
        cur = conn.cursor()

        if DATABASE_URL:
            # PostgreSQL: use INSERT ... ON CONFLICT DO NOTHING
            # First try with primary key constraint; if it doesn't exist, use DO NOTHING without specifying conflict target
            quoted_cols  = ', '.join([f'"{c}"' for c in df_to_store.columns])
            placeholders = ', '.join(['%s'] * len(df_to_store.columns))

            # Try with explicit conflict target first
            try:
                sql = (f'INSERT INTO {TABLE_NAME} ({quoted_cols}) VALUES ({placeholders}) '
                       f'ON CONFLICT ("stationId", "timestampDate") DO NOTHING')
                data = [tuple(None if (v != v) else v for v in row)
                        for row in df_to_store.to_numpy()]
                cur.executemany(sql, data)
                conn.commit()
                print(f"✅ Inserted {len(data)} records (with conflict target).")
            except Exception as e1:
                conn.rollback()
                print(f"⚠️  Conflict target failed ({e1}), trying without conflict target...")
                # Fallback: no conflict target — just skip duplicates using DO NOTHING
                # This requires a unique constraint or primary key to exist for DO NOTHING to work
                # If none exists, use a plain INSERT and catch duplicate errors
                try:
                    sql = (f'INSERT INTO {TABLE_NAME} ({quoted_cols}) VALUES ({placeholders})')
                    data = [tuple(None if (v != v) else v for v in row)
                            for row in df_to_store.to_numpy()]
                    for row in data:
                        try:
                            cur.execute(sql, row)
                        except Exception:
                            conn.rollback()
                            cur = conn.cursor()  # reset cursor after rollback
                    conn.commit()
                    print(f"✅ Inserted records (row-by-row, skipping errors).")
                except Exception as e2:
                    conn.rollback()
                    print(f"🔴 Insert failed: {e2}")
        else:
            # SQLite
            quoted_cols  = ', '.join([f'"{c}"' for c in df_to_store.columns])
            placeholders = ', '.join(['?'] * len(df_to_store.columns))
            sql  = f'INSERT OR REPLACE INTO "{TABLE_NAME}" ({quoted_cols}) VALUES ({placeholders})'
            data = [tuple(None if (isinstance(v, float) and np.isnan(v)) else v for v in row)
                    for row in df_to_store.to_numpy()]
            cur.executemany(sql, data)
            conn.commit()
            print(f"✅ Inserted {len(data)} records.")

    except Exception as e:
        print(f"🔴 DB error: {e}")
        import traceback; traceback.print_exc()
    finally:
        conn.close()

    print(f"[{datetime.now()}] --- Database Update Pipeline Finished ---")


if __name__ == "__main__":
    preprocess_and_store_data()
