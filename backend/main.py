
# # backend/main.py
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from flask_compress import Compress
# import json
# import os
# import pandas as pd
# from datetime import datetime

# BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# # Paths
# LOCATIONS_CSV_PATH   = os.path.join(BACKEND_DIR, "data/cpcb_station_locations.csv")
# STATIC_DIR           = os.path.join(BACKEND_DIR, "static")
# DAILY_PRED_DIR       = os.path.join(STATIC_DIR, "predictions/daily")
# WEEKLY_PRED_DIR      = os.path.join(STATIC_DIR, "predictions/weekly")
# DAYNIGHT_DIR         = os.path.join(STATIC_DIR, "daynight")
# ANOMALY_PLOT_PATH    = os.path.join(STATIC_DIR, "anomaly/anomaly_heatmap.json")
# CORRELATION_DIR      = os.path.join(STATIC_DIR, "correlation")
# WEEKLY_DETAILS_DIR   = os.path.join(STATIC_DIR, "predictions/weekly_details")
# DAILY_SUMMARY_PATH   = os.path.join(STATIC_DIR, "predictions/daily_summary_predictions.json")
# WEEKLY_SUMMARY_PATH  = os.path.join(STATIC_DIR, "predictions/weekly_summary_predictions.json")
# STATION_QUALITY_PATH = os.path.join(STATIC_DIR, "station_quality.json")

# TABLE_NAME = "water_records"

# # ── Flask app ──────────────────────────────────────────────────────────────────
# app = Flask(__name__, static_folder=STATIC_DIR)
# CORS(app)        # fully open — allows all origins
# Compress(app)    # gzip compression

# # ── Load heavy dependencies safely (won't crash server if missing) ─────────────
# try:
#     from models.classification import predict_water_quality, features as classification_features
#     CLASSIFICATION_AVAILABLE = True
#     print("✅ Classification model loaded.")
# except Exception as e:
#     print(f"⚠️  Classification model NOT loaded: {e}")
#     CLASSIFICATION_AVAILABLE = False
#     classification_features = []
#     def predict_water_quality(x):
#         return {"status": "error", "message": "Model not available"}

# try:
#     from db import read_sql, DATABASE_URL
#     DB_AVAILABLE = True
#     print(f"✅ DB helper loaded. Using: {'Supabase' if DATABASE_URL else 'SQLite'}")
# except Exception as e:
#     print(f"⚠️  DB helper NOT loaded: {e}")
#     DB_AVAILABLE = False
#     DATABASE_URL = None
#     def read_sql(q, params=None):
#         raise RuntimeError("DB not available")


# # ── Helper ─────────────────────────────────────────────────────────────────────
# def read_json_file(path):
#     if not os.path.exists(path):
#         return None, f"File not found: {path}"
#     try:
#         with open(path, 'r') as f:
#             return json.load(f), None
#     except Exception as e:
#         return None, str(e)


# # ── Health check ───────────────────────────────────────────────────────────────
# @app.route('/', methods=['GET', 'HEAD'])
# def health_check():
#     return jsonify({
#         "status": "ok",
#         "db": "supabase" if DATABASE_URL else "sqlite",
#         "classification": CLASSIFICATION_AVAILABLE,
#         "db_available": DB_AVAILABLE,
#     })

# @app.route('/api/health', methods=['GET'])
# def api_health():
#     return jsonify({"status": "ok"})

# @app.route('/api/debug-db', methods=['GET'])
# def debug_db():
#     try:
#         # Get column names and first 2 rows
#         df = read_sql("SELECT * FROM water_records LIMIT 2")
#         return jsonify({
#             "columns": list(df.columns),
#             "row_count_sample": len(df),
#             "first_row": df.iloc[0].to_dict() if len(df) > 0 else {}
#         })
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # ── Stations ───────────────────────────────────────────────────────────────────
# @app.route('/api/stations', methods=['GET'])
# def get_stations():
#     # Load location CSV
#     try:
#         locations_df = pd.read_csv(LOCATIONS_CSV_PATH)
#         locations_df = locations_df[
#             ['station_id', 'station_name', 'latitude', 'longitude', 'state']
#         ].rename(columns={
#             'station_id':   'stationId',
#             'station_name': 'name',
#             'latitude':     'lat',
#             'longitude':    'lng',
#             'state':        'location'
#         })
#         locations_df['stationId'] = pd.to_numeric(
#             locations_df['stationId'], errors='coerce'
#         ).dropna().astype(int)
#     except Exception as e:
#         print(f"ERROR loading locations CSV: {e}")
#         return jsonify({"error": f"Failed to load station location data: {e}"}), 500

#     # Fast path — pre-computed quality file
#     if os.path.exists(STATION_QUALITY_PATH):
#         try:
#             with open(STATION_QUALITY_PATH, 'r') as f:
#                 quality_map = json.load(f)
#             locations_df['quality'] = (
#                 locations_df['stationId'].astype(str).map(quality_map).fillna('Medium')
#             )
#             print(f"✅ Returning {len(locations_df)} stations from quality file.")
#             return jsonify(locations_df.to_dict('records'))
#         except Exception as e:
#             print(f"Warning: quality file failed: {e}")

#     # Fallback — assign Medium to all (avoids slow DB call / timeout)
#     locations_df['quality'] = 'Medium'
#     print(f"⚠️  No quality file — returning {len(locations_df)} stations with Medium quality.")
#     return jsonify(locations_df.to_dict('records'))


# # ── Classification ─────────────────────────────────────────────────────────────
# @app.route('/api/classify', methods=['POST'])
# def handle_classification():
#     if not CLASSIFICATION_AVAILABLE:
#         return jsonify({"status": "error", "message": "Classification model not loaded."}), 503
#     try:
#         user_input = request.json
#         result = predict_water_quality(user_input)
#         if result['status'] == 'error':
#             return jsonify(result), 400
#         return jsonify(result)
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)}), 500


# # ── Latest DB data ─────────────────────────────────────────────────────────────
# @app.route('/api/latest-cpcb-data', methods=['GET'])
# def get_latest_db_data():
#     if not DB_AVAILABLE:
#         return jsonify({"error": "Database not available on server."}), 503

#     try:
#         locations_df = pd.read_csv(LOCATIONS_CSV_PATH)
#         locations_df = locations_df[['station_id', 'station_name', 'state']].rename(columns={
#             'station_id':   'stationId',
#             'station_name': 'stationName',
#             'state':        'location'
#         })
#         locations_df['stationId'] = pd.to_numeric(
#             locations_df['stationId'], errors='coerce'
#         ).astype('Int64')
#     except Exception as e:
#         return jsonify({"error": f"Failed to load location data: {e}"}), 500

#     try:
#         query = """
#         SELECT t1.* FROM water_records t1
#         INNER JOIN (
#             SELECT "stationId", MAX("timestampDate") as MaxTimestamp
#             FROM water_records GROUP BY "stationId"
#         ) t2 ON t1."stationId" = t2."stationId"
#            AND t1."timestampDate" = t2.MaxTimestamp
#         """
#         latest_df = read_sql(query)
#         latest_df['stationId'] = pd.to_numeric(
#             latest_df['stationId'], errors='coerce'
#         ).astype('Int64')
#         if 'timestampDate' in latest_df.columns:
#             latest_df['timestamp'] = (
#                 pd.to_datetime(latest_df['timestampDate'], errors='coerce')
#                   .dt.strftime('%Y-%m-%d %H:%M:%S')
#             )
#     except Exception as e:
#         print(f"ERROR fetching DB data: {e}")
#         return jsonify({"error": f"Failed to fetch data from database: {e}"}), 500

#     if latest_df.empty:
#         return jsonify({"data": [], "last_fetched": datetime.now().isoformat()})

#     try:
#         merged_df = pd.merge(latest_df, locations_df, on='stationId', how='left')
#         non_param = {'stationId', 'stationName', 'location', 'timestamp', 'timestampDate', 'id'}
#         param_cols = sorted([c for c in merged_df.columns if c not in non_param])
#         ordered = ['stationId', 'stationName', 'location', 'timestamp'] + param_cols
#         ordered = [c for c in ordered if c in merged_df.columns]
#         data_list = (
#             merged_df[ordered]
#             .where(pd.notnull(merged_df[ordered]), None)
#             .to_dict('records')
#         )
#         return jsonify({"data": data_list, "last_fetched": datetime.now().isoformat()})
#     except Exception as e:
#         return jsonify({"error": f"Failed to process data: {e}"}), 500


# # ── Prediction endpoints ───────────────────────────────────────────────────────
# @app.route('/api/predictions/daily/<station_id>', methods=['GET'])
# def get_daily_prediction(station_id):
#     data, err = read_json_file(
#         os.path.join(DAILY_PRED_DIR, f"daily_pred_station_{station_id}.json")
#     )
#     if err: return jsonify({"error": "Prediction not found for this station."}), 404
#     return jsonify(data)

# @app.route('/api/predictions/weekly/<station_id>', methods=['GET'])
# def get_weekly_prediction(station_id):
#     data, err = read_json_file(
#         os.path.join(WEEKLY_PRED_DIR, f"weekly_pred_station_{station_id}.json")
#     )
#     if err: return jsonify({"error": "Prediction not found for this station."}), 404
#     return jsonify(data)

# @app.route('/api/predictions/weekly_details/<station_id>', methods=['GET'])
# def get_weekly_details(station_id):
#     data, err = read_json_file(
#         os.path.join(WEEKLY_DETAILS_DIR, f"weekly_details_station_{station_id}.json")
#     )
#     if err: return jsonify({"error": "Weekly details not found for this station."}), 404
#     return jsonify(data)

# @app.route('/api/predictions/summary/daily', methods=['GET'])
# def get_daily_summary():
#     data, err = read_json_file(DAILY_SUMMARY_PATH)
#     if err: return jsonify({"error": "Daily summary not found. Run batch jobs first."}), 404
#     return jsonify(data)

# @app.route('/api/predictions/summary/weekly', methods=['GET'])
# def get_weekly_summary():
#     data, err = read_json_file(WEEKLY_SUMMARY_PATH)
#     if err: return jsonify({"error": "Weekly summary not found. Run batch jobs first."}), 404
#     return jsonify(data)


# # ── Analysis endpoints ─────────────────────────────────────────────────────────
# @app.route('/api/anomaly-heatmap', methods=['GET'])
# def get_anomaly_map():
#     data, err = read_json_file(ANOMALY_PLOT_PATH)
#     if err: return jsonify({"error": "Anomaly heatmap not found. Run batch jobs first."}), 404
#     return jsonify(data)

# @app.route('/api/correlation/<station_id>', methods=['GET'])
# def get_correlation_plot(station_id):
#     method = request.args.get('method', 'spearman').lower()
#     if method not in ['pearson', 'spearman', 'kendall']:
#         method = 'spearman'
#     data, err = read_json_file(
#         os.path.join(CORRELATION_DIR, f"correlation_station_{station_id}_{method}.json")
#     )
#     if err:
#         return jsonify({"error": f"Correlation plot not found for station {station_id}."}), 404
#     return jsonify(data)

# @app.route('/api/daynight/list', methods=['GET'])
# def list_daynight_plots():
#     try:
#         if not os.path.exists(DAYNIGHT_DIR):
#             return jsonify([])
#         files = [f for f in os.listdir(DAYNIGHT_DIR) if f.endswith(".png")]
#         return jsonify(files)
#     except Exception as e:
#         return jsonify({"error": f"Failed to list files: {e}"}), 500


# # ── Run ────────────────────────────────────────────────────────────────────────
# if __name__ == '__main__':
#     app.run(debug=True, port=5000, use_reloader=False)


# backend/main.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_compress import Compress
import json
import os
import pandas as pd
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

LOCATIONS_CSV_PATH   = os.path.join(BACKEND_DIR, "data/cpcb_station_locations.csv")
STATIC_DIR           = os.path.join(BACKEND_DIR, "static")
DAILY_PRED_DIR       = os.path.join(STATIC_DIR, "predictions/daily")
WEEKLY_PRED_DIR      = os.path.join(STATIC_DIR, "predictions/weekly")
DAYNIGHT_DIR         = os.path.join(STATIC_DIR, "daynight")
ANOMALY_PLOT_PATH    = os.path.join(STATIC_DIR, "anomaly/anomaly_heatmap.json")
CORRELATION_DIR      = os.path.join(STATIC_DIR, "correlation")
WEEKLY_DETAILS_DIR   = os.path.join(STATIC_DIR, "predictions/weekly_details")
DAILY_SUMMARY_PATH   = os.path.join(STATIC_DIR, "predictions/daily_summary_predictions.json")
WEEKLY_SUMMARY_PATH  = os.path.join(STATIC_DIR, "predictions/weekly_summary_predictions.json")
STATION_QUALITY_PATH = os.path.join(STATIC_DIR, "station_quality.json")

app = Flask(__name__, static_folder=STATIC_DIR)
app.url_map.strict_slashes = False
CORS(app)
Compress(app)

# ── Load dependencies safely ───────────────────────────────────────────────────
try:
    from models.classification import predict_water_quality, features as classification_features
    CLASSIFICATION_AVAILABLE = True
    print("✅ Classification model loaded.")
except Exception as e:
    print(f"⚠️  Classification model NOT loaded: {e}")
    CLASSIFICATION_AVAILABLE = False
    classification_features = []
    def predict_water_quality(x):
        return {"status": "error", "message": "Model not available"}

try:
    from db import read_sql, DATABASE_URL
    DB_AVAILABLE = True
    print(f"✅ DB loaded. Using: {'Supabase' if DATABASE_URL else 'SQLite'}")
except Exception as e:
    print(f"⚠️  DB NOT loaded: {e}")
    DB_AVAILABLE = False
    DATABASE_URL = None
    def read_sql(q, params=None):
        raise RuntimeError("DB not available")

# ── Detect actual column names in DB (handles Supabase lowercase) ──────────────
STATION_ID_COL    = "stationId"      # will be updated after first successful query
TIMESTAMP_COL     = "timestampDate"  # will be updated after first successful query
COLS_DETECTED     = False

def detect_db_columns():
    global STATION_ID_COL, TIMESTAMP_COL, COLS_DETECTED
    if COLS_DETECTED or not DB_AVAILABLE:
        return
    try:
        df = read_sql("SELECT * FROM water_records LIMIT 1")
        cols = list(df.columns)
        print(f"DB columns detected: {cols}")
        # Find stationId column
        for candidate in ['stationId', 'stationid', 'station_id', 'StationId']:
            if candidate in cols:
                STATION_ID_COL = candidate
                break
        # Find timestampDate column
        for candidate in ['timestampDate', 'timestampdate', 'timestamp_date', 'TimestampDate']:
            if candidate in cols:
                TIMESTAMP_COL = candidate
                break
        COLS_DETECTED = True
        print(f"Using stationId col: '{STATION_ID_COL}', timestamp col: '{TIMESTAMP_COL}'")
    except Exception as e:
        print(f"⚠️  Could not detect DB columns: {e}")

# Run detection at startup
detect_db_columns()


# ── Helpers ────────────────────────────────────────────────────────────────────
def read_json_file(path):
    if not os.path.exists(path):
        return None, f"File not found: {path}"
    try:
        with open(path, 'r') as f:
            return json.load(f), None
    except Exception as e:
        return None, str(e)


def get_latest_query():
    """Returns the correct DISTINCT ON query using detected column names."""
    sid = STATION_ID_COL
    ts  = TIMESTAMP_COL
    return f"""
        SELECT DISTINCT ON ("{sid}") *
        FROM water_records
        ORDER BY "{sid}", "{ts}" DESC NULLS LAST
    """

# ── Health check ───────────────────────────────────────────────────────────────
@app.route('/', methods=['GET', 'HEAD'])
def health_check():
    return jsonify({
        "status": "ok",
        "db": "supabase" if DATABASE_URL else "sqlite",
        "classification": CLASSIFICATION_AVAILABLE,
        "db_available": DB_AVAILABLE,
        "station_id_col": STATION_ID_COL,
        "timestamp_col": TIMESTAMP_COL,
    })

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({"status": "ok"})

@app.route('/api/debug-db', methods=['GET'])
def debug_db():
    """Temporary debug endpoint — shows actual DB columns and sample row."""
    if not DB_AVAILABLE:
        return jsonify({"error": "DB not available"}), 503
    try:
        df = read_sql("SELECT * FROM water_records LIMIT 2")
        return jsonify({
            "columns": list(df.columns),
            "row_count_in_sample": len(df),
            "first_row": {k: str(v) for k, v in df.iloc[0].to_dict().items()} if len(df) > 0 else {},
            "station_id_col_detected": STATION_ID_COL,
            "timestamp_col_detected": TIMESTAMP_COL,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Stations ───────────────────────────────────────────────────────────────────
@app.route('/api/stations', methods=['GET'])
def get_stations():
    try:
        locations_df = pd.read_csv(LOCATIONS_CSV_PATH)
        locations_df = locations_df[
            ['station_id', 'station_name', 'latitude', 'longitude', 'state']
        ].rename(columns={
            'station_id': 'stationId', 'station_name': 'name',
            'latitude': 'lat', 'longitude': 'lng', 'state': 'location'
        })
        locations_df['stationId'] = pd.to_numeric(locations_df['stationId'], errors='coerce')
        locations_df = locations_df.dropna(subset=['stationId'])
        locations_df['stationId'] = locations_df['stationId'].astype(int)
    except Exception as e:
        return jsonify({"error": f"Failed to load station data: {e}"}), 500

    if os.path.exists(STATION_QUALITY_PATH):
        try:
            with open(STATION_QUALITY_PATH, 'r') as f:
                quality_map = json.load(f)
            locations_df['quality'] = locations_df['stationId'].astype(str).map(quality_map).fillna('Medium')
            return jsonify(locations_df.to_dict('records'))
        except Exception as e:
            print(f"Quality file failed: {e}")

    locations_df['quality'] = 'Medium'
    return jsonify(locations_df.to_dict('records'))


# ── Classification ─────────────────────────────────────────────────────────────
@app.route('/api/classify', methods=['POST', 'OPTIONS'])
def handle_classification():
    if request.method == 'OPTIONS':
        return '', 204
    if not CLASSIFICATION_AVAILABLE:
        return jsonify({"status": "error", "message": "Model not loaded."}), 503
    try:
        result = predict_water_quality(request.json)
        return jsonify(result), (400 if result['status'] == 'error' else 200)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Latest DB data ─────────────────────────────────────────────────────────────
@app.route('/api/latest-cpcb-data', methods=['GET'])
def get_latest_db_data():
    if not DB_AVAILABLE:
        return jsonify({"error": "Database not available."}), 503

    try:
        locations_df = pd.read_csv(LOCATIONS_CSV_PATH)
        locations_df = locations_df[['station_id', 'station_name', 'state']].rename(columns={
            'station_id': 'stationId', 'station_name': 'stationName', 'state': 'location'
        })
        locations_df['stationId'] = pd.to_numeric(locations_df['stationId'], errors='coerce').astype('Int64')
    except Exception as e:
        return jsonify({"error": f"Failed to load location data: {e}"}), 500

    try:
        # Use DISTINCT ON — works for Postgres (Supabase)
        # Falls back to simpler query for SQLite
        if DATABASE_URL:
            query = get_latest_query()
        else:
            query = f"""
                SELECT t1.* FROM water_records t1
                INNER JOIN (
                    SELECT "{STATION_ID_COL}", MAX("{TIMESTAMP_COL}") as MaxTS
                    FROM water_records GROUP BY "{STATION_ID_COL}"
                ) t2 ON t1."{STATION_ID_COL}" = t2."{STATION_ID_COL}"
                   AND t1."{TIMESTAMP_COL}" = t2.MaxTS
            """
        latest_df = read_sql(query)

        # Normalise column names to camelCase for the frontend
        rename_map = {}
        for col in latest_df.columns:
            if col.lower() == 'stationid':    rename_map[col] = 'stationId'
            if col.lower() == 'timestampdate': rename_map[col] = 'timestampDate'
            if col.lower() == 'timestamp':     rename_map[col] = 'timestamp'
        latest_df = latest_df.rename(columns=rename_map)

        latest_df['stationId'] = pd.to_numeric(latest_df.get('stationId', latest_df.iloc[:, 0]), errors='coerce').astype('Int64')
        if 'timestampDate' in latest_df.columns:
            latest_df['timestamp'] = pd.to_datetime(latest_df['timestampDate'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    except Exception as e:
        print(f"DB query error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"DB query failed: {e}"}), 500

    if latest_df.empty:
        return jsonify({"data": [], "last_fetched": datetime.now().isoformat()})

    try:
        merged_df = pd.merge(latest_df, locations_df, on='stationId', how='left')
        non_param = {'stationId', 'stationName', 'location', 'timestamp', 'timestampDate', 'id'}
        param_cols = sorted([c for c in merged_df.columns if c not in non_param])
        ordered = [c for c in ['stationId', 'stationName', 'location', 'timestamp'] + param_cols if c in merged_df.columns]
        data_list = merged_df[ordered].where(pd.notnull(merged_df[ordered]), None).to_dict('records')
        return jsonify({"data": data_list, "last_fetched": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"error": f"Failed to process data: {e}"}), 500


# ── Prediction endpoints ───────────────────────────────────────────────────────
@app.route('/api/predictions/daily/<station_id>', methods=['GET'])
def get_daily_prediction(station_id):
    data, err = read_json_file(os.path.join(DAILY_PRED_DIR, f"daily_pred_station_{station_id}.json"))
    return jsonify({"error": "Not found."}) if err else jsonify(data)

@app.route('/api/predictions/weekly/<station_id>', methods=['GET'])
def get_weekly_prediction(station_id):
    data, err = read_json_file(os.path.join(WEEKLY_PRED_DIR, f"weekly_pred_station_{station_id}.json"))
    return (jsonify({"error": "Not found."}), 404) if err else jsonify(data)

@app.route('/api/predictions/weekly_details/<station_id>', methods=['GET'])
def get_weekly_details(station_id):
    data, err = read_json_file(os.path.join(WEEKLY_DETAILS_DIR, f"weekly_details_station_{station_id}.json"))
    return (jsonify({"error": "Not found."}), 404) if err else jsonify(data)

@app.route('/api/predictions/summary/daily', methods=['GET'])
def get_daily_summary():
    data, err = read_json_file(DAILY_SUMMARY_PATH)
    return (jsonify({"error": "Run batch jobs first."}), 404) if err else jsonify(data)

@app.route('/api/predictions/summary/weekly', methods=['GET'])
def get_weekly_summary():
    data, err = read_json_file(WEEKLY_SUMMARY_PATH)
    return (jsonify({"error": "Run batch jobs first."}), 404) if err else jsonify(data)


# ── Analysis endpoints ─────────────────────────────────────────────────────────
@app.route('/api/anomaly-heatmap', methods=['GET'])
def get_anomaly_map():
    data, err = read_json_file(ANOMALY_PLOT_PATH)
    return (jsonify({"error": "Run batch jobs first."}), 404) if err else jsonify(data)

@app.route('/api/correlation/<station_id>', methods=['GET'])
def get_correlation_plot(station_id):
    method = request.args.get('method', 'spearman').lower()
    if method not in ['pearson', 'spearman', 'kendall']:
        method = 'spearman'
    data, err = read_json_file(os.path.join(CORRELATION_DIR, f"correlation_station_{station_id}_{method}.json"))
    return (jsonify({"error": "Not found."}), 404) if err else jsonify(data)

@app.route('/api/daynight/list', methods=['GET'])
def list_daynight_plots():
    try:
        if not os.path.exists(DAYNIGHT_DIR):
            return jsonify([])
        return jsonify([f for f in os.listdir(DAYNIGHT_DIR) if f.endswith(".png")])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)

