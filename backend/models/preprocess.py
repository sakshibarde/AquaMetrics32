# # models/preprocess.py
# import pandas as pd
# import sqlite3
# from sklearn.preprocessing import StandardScaler
# import os

# # --- FIX: Use absolute path ---
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# # SCRIPT_DIR is .../backend/models
# # os.path.dirname(SCRIPT_DIR) is .../backend
# BACKEND_DIR = os.path.dirname(SCRIPT_DIR) 
# DB_PATH = os.path.join(BACKEND_DIR, "database/water_quality.db") # Corrected Path
# DB_DIR = os.path.dirname(DB_PATH)
# os.makedirs(DB_DIR, exist_ok=True)
# # --- END FIX ---

# TABLE_NAME = "water_records"

# def organize_records(df: pd.DataFrame):
#     # Pivot: stationId + timestamp + timestampDate → columns = parameterName
#     pivot_df = df.pivot_table(
#         index=['stationId', 'timestamp', 'timestampDate'],
#         columns='parameterName',
#         values='value',
#         aggfunc='first'
#     ).reset_index()

#     # Drop malfunctioning station IDs
#     ids_to_drop = [11791, 11792, 11810]
#     pivot_df = pivot_df[~pivot_df['stationId'].isin(ids_to_drop)]
#     return pivot_df

# def clean_and_fill(df_new: pd.DataFrame):
#     conn = sqlite3.connect(DB_PATH)

#     # --- 1. ADD TIMESTAMP CONVERSION ---
#     print("Parsing timestamp...")
#     if 'timestamp' not in df_new.columns:
#         print("🔴 ERROR: 'timestamp' column missing in data.")
#         return pd.DataFrame() # Return empty
#     try:
#         # Assuming timestamp string is like 'YYYY-MM-DD HH:MM:SS'
#         df_new['timestampDate'] = pd.to_datetime(df_new['timestamp'], errors='coerce')
#     except Exception as e:
#         print(f"🔴 ERROR converting 'timestamp' column: {e}")
#         df_new['timestampDate'] = pd.NaT

#     # Drop rows where timestamp couldn't be parsed
#     df_new = df_new.dropna(subset=['timestampDate'])
#     if df_new.empty:
#         print("🟡 No valid data remaining after timestamp parsing.")
#         return df_new

#     # --- 1. Load historical data (for mean reference) ---
#     try:
#         df_hist = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
#     except Exception as e:
#         print(f"Warning: Could not load historical data for mean calc. {e}")
#         df_hist = pd.DataFrame()
#     finally:
#         conn.close()

#     # --- 2. Drop too-incomplete rows in new data ---
#     df_new = df_new[df_new.isnull().sum(axis=1) <= 3].copy()
    
#     numeric_cols = df_new.select_dtypes(include=['number']).columns

#     # --- 3. Combine historical + new (only for computing means) ---
#     if not df_hist.empty:
#         hist_numeric_cols = df_hist.select_dtypes(include=['number']).columns
#         # Ensure we only use common columns
#         common_cols = list(set(numeric_cols) & set(hist_numeric_cols))
#         combined = pd.concat([df_hist[common_cols], df_new[common_cols]], ignore_index=True)
#         col_means = combined.mean()
#     else:
#         col_means = df_new[numeric_cols].mean()

#     # --- 4. Fill missing numeric values in the new batch ---
#     df_new[numeric_cols] = df_new[numeric_cols].fillna(col_means)

#     # Note: Standardization is removed here.
#     # Each model (classification, LSTM) should handle its own scaling
#     # by loading its own specific scaler.
#     return df_new


# backend/models/preprocess.py
import pandas as pd
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)
from db import read_sql


def organize_records(df: pd.DataFrame):
    pivot_df = df.pivot_table(
        index=['stationId', 'timestamp', 'timestampDate'],
        columns='parameterName',
        values='value',
        aggfunc='first'
    ).reset_index()

    ids_to_drop = [11791, 11792, 11810]
    pivot_df = pivot_df[~pivot_df['stationId'].isin(ids_to_drop)]
    return pivot_df


def clean_and_fill(df_new: pd.DataFrame):
    # 1. Parse timestamp
    print("Parsing timestamp...")
    if 'timestamp' not in df_new.columns:
        print("🔴 ERROR: 'timestamp' column missing.")
        return pd.DataFrame()
    try:
        df_new['timestampDate'] = pd.to_datetime(df_new['timestamp'], errors='coerce')
    except Exception as e:
        print(f"🔴 ERROR converting 'timestamp': {e}")
        df_new['timestampDate'] = pd.NaT

    df_new = df_new.dropna(subset=['timestampDate'])
    if df_new.empty:
        print("No valid data after timestamp parsing.")
        return df_new

    # 2. Load historical data for mean reference
    try:
        df_hist = read_sql("SELECT * FROM water_records")
    except Exception as e:
        print(f"Warning: Could not load historical data: {e}")
        df_hist = pd.DataFrame()

    # 3. Drop too-incomplete rows
    df_new = df_new[df_new.isnull().sum(axis=1) <= 3].copy()
    numeric_cols = df_new.select_dtypes(include=['number']).columns

    # 4. Compute column means from combined history + new
    if not df_hist.empty:
        hist_numeric_cols = df_hist.select_dtypes(include=['number']).columns
        common_cols = list(set(numeric_cols) & set(hist_numeric_cols))
        combined = pd.concat([df_hist[common_cols], df_new[common_cols]], ignore_index=True)
        col_means = combined.mean()
    else:
        col_means = df_new[numeric_cols].mean()

    # 5. Fill missing values
    df_new[numeric_cols] = df_new[numeric_cols].fillna(col_means)

    return df_new