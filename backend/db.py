# # backend/db.py
# # This file handles database connections.
# # Locally (no DATABASE_URL set) → uses SQLite
# # In production (DATABASE_URL set) → uses Supabase (PostgreSQL)

# import os
# import pandas as pd

# DATABASE_URL = os.environ.get('DATABASE_URL')  # None locally, set in prod

# def get_connection():
#     """Returns a database connection — sqlite3 locally, psycopg2 in production."""
#     if DATABASE_URL:
#         import psycopg2
#         return psycopg2.connect(DATABASE_URL)
#     else:
#         import sqlite3
#         db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database/water_quality.db')
#         return sqlite3.connect(db_path)

# def read_sql(query, params=None):
#     """Runs a SELECT query and returns a pandas DataFrame."""
#     conn = get_connection()
#     try:
#         return pd.read_sql_query(query, conn, params=params)
#     finally:
#         conn.close()

# def get_placeholder():
#     """Returns the correct SQL placeholder for the active DB."""
#     return '%s' if DATABASE_URL else '?'

# def get_upsert_sql(table, columns):
#     """
#     Returns the correct INSERT/UPSERT SQL for the active DB.
#     PostgreSQL uses ON CONFLICT DO NOTHING, SQLite uses INSERT OR REPLACE.
#     """
#     placeholder = get_placeholder()
#     quoted_cols = ', '.join([f'"{col}"' for col in columns])
#     placeholders = ', '.join([placeholder] * len(columns))

#     if DATABASE_URL:
#         return f'INSERT INTO {table} ({quoted_cols}) VALUES ({placeholders}) ON CONFLICT ("stationId", "timestampDate") DO NOTHING'
#     else:
#         return f'INSERT OR REPLACE INTO "{table}" ({quoted_cols}) VALUES ({placeholders})'

# def execute_many(sql, data_tuples):
#     """Runs an executemany for INSERT/UPDATE operations."""
#     conn = get_connection()
#     try:
#         cur = conn.cursor()
#         cur.executemany(sql, data_tuples)
#         conn.commit()
#         print(f"✅ Inserted/updated {len(data_tuples)} records.")
#     finally:
#         conn.close()

# def execute_ddl(sql):
#     """Runs a CREATE TABLE or similar DDL statement."""
#     conn = get_connection()
#     try:
#         cur = conn.cursor()
#         cur.execute(sql)
#         conn.commit()
#     finally:
#         conn.close()




# backend/db.py
import os
import pandas as pd

DATABASE_URL = os.environ.get('DATABASE_URL')


def get_connection():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    else:
        import sqlite3
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database/water_quality.db')
        return sqlite3.connect(db_path)


def read_sql(query, params=None):
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def get_placeholder():
    return '%s' if DATABASE_URL else '?'


def get_upsert_sql(table, columns):
    placeholder = get_placeholder()
    quoted_cols = ', '.join([f'"{col}"' for col in columns])
    placeholders = ', '.join([placeholder] * len(columns))
    if DATABASE_URL:
        return f'INSERT INTO {table} ({quoted_cols}) VALUES ({placeholders}) ON CONFLICT ("stationId", "timestampDate") DO NOTHING'
    else:
        return f'INSERT OR REPLACE INTO "{table}" ({quoted_cols}) VALUES ({placeholders})'


def execute_many(sql, data_tuples):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany(sql, data_tuples)
        conn.commit()
        print(f"✅ Inserted/updated {len(data_tuples)} records.")
    finally:
        conn.close()


def execute_ddl(sql):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
    finally:
        conn.close()


def get_column_names(table='water_records'):
    """Returns actual column names from the DB — handles lowercase Supabase columns."""
    try:
        df = read_sql(f"SELECT * FROM {table} LIMIT 1")
        return list(df.columns)
    except Exception as e:
        print(f"Could not get column names: {e}")
        return []


def detect_column(candidates, actual_columns):
    """
    Given a list of possible column name variants, return the one that exists.
    e.g. detect_column(['stationId', 'stationid'], actual_columns)
    """
    actual_lower = {c.lower(): c for c in actual_columns}
    for candidate in candidates:
        if candidate in actual_columns:
            return candidate
        if candidate.lower() in actual_lower:
            return actual_lower[candidate.lower()]
    return candidates[0]  # fallback to first candidate
