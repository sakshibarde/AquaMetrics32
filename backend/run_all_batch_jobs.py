# # run_all_batch_jobs.py
# import time
# from models.daynight_analysis import run_day_night_analysis
# from models.anomaly_detection import run_anomaly_detection
# from models.predictions import create_daily_prediction_plots, create_weekly_prediction_plots
# from models.correlation_analysis import run_correlation_analysis # <-- (NEW) IMPORT

# if __name__ == "__main__":
#     start_time = time.time()
#     print("--- 🚀 Starting All Daily Batch Jobs ---")
    
#     run_day_night_analysis()
#     run_anomaly_detection()
#     create_daily_prediction_plots()
#     create_weekly_prediction_plots()
#     run_correlation_analysis() # <-- (NEW) ADD TO LIST
    
#     end_time = time.time()
#     print(f"--- ✅ All Daily Batch Jobs Complete (Total time: {end_time - start_time:.2f}s) ---")


# backend/run_all_batch_jobs.py
import time
import json
import os
import sys
import pandas as pd

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from models.daynight_analysis import run_day_night_analysis
from models.anomaly_detection import run_anomaly_detection
from models.predictions import create_daily_prediction_plots, create_weekly_prediction_plots
from models.correlation_analysis import run_correlation_analysis
from db import read_sql


def precompute_station_quality():
    """
    Classifies the latest reading for every station and saves the results
    to static/station_quality.json so /api/stations is fast (no live ML at request time).
    """
    print("--- Pre-computing Station Quality ---")
    try:
        from models.classification import predict_water_quality, features as classification_features
    except Exception as e:
        print(f"🔴 Could not load classification model: {e}")
        return

    try:
        query = """
        SELECT t1.* FROM water_records t1
        INNER JOIN (
            SELECT "stationId", MAX("timestampDate") as MaxTimestamp
            FROM water_records GROUP BY "stationId"
        ) t2 ON t1."stationId" = t2."stationId" AND t1."timestampDate" = t2.MaxTimestamp
        """
        latest_df = read_sql(query)
    except Exception as e:
        print(f"🔴 ERROR reading DB for quality precompute: {e}")
        return

    quality_map = {}
    for _, row in latest_df.iterrows():
        station_id = str(row['stationId'])
        input_data = {
            feat: row.get(feat, 0) if pd.notna(row.get(feat)) else 0
            for feat in classification_features
        }
        result = predict_water_quality(input_data)
        quality_map[station_id] = result['class'] if result['status'] == 'success' else 'Medium'

    output_path = os.path.join(BACKEND_DIR, "static/station_quality.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(quality_map, f)
    print(f"✅ Station quality saved to {output_path} ({len(quality_map)} stations)")


if __name__ == "__main__":
    start_time = time.time()
    print("--- 🚀 Starting All Daily Batch Jobs ---")

    run_day_night_analysis()
    run_anomaly_detection()
    create_daily_prediction_plots()
    create_weekly_prediction_plots()
    run_correlation_analysis()
    precompute_station_quality()   # <-- new: makes /api/stations fast

    end_time = time.time()
    print(f"--- ✅ All Daily Batch Jobs Complete (Total: {end_time - start_time:.2f}s) ---")