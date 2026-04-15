# # backend/models/anomaly_detection.py
# import pandas as pd
# import numpy as np
# from keras.models import Sequential
# from keras.layers import LSTM, RepeatVector, TimeDistributed, Dense
# from sklearn.preprocessing import MinMaxScaler
# import plotly.graph_objects as go
# import json
# import os
# import sys
# import warnings

# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
# warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')

# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
# sys.path.insert(0, BACKEND_DIR)
# from db import read_sql

# OUTPUT_JSON = os.path.join(BACKEND_DIR, "static/anomaly/anomaly_heatmap.json")
# WINDOW_SIZE = 30


# def run_anomaly_detection():
#     print("--- Starting Anomaly Detection Batch Job ---")
#     os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)

#     try:
#         df = read_sql("SELECT * FROM water_records")
#         df['timestampDate'] = pd.to_datetime(df['timestampDate'], errors='coerce')
#     except Exception as e:
#         print(f"🔴 ERROR: Could not read from database: {e}")
#         return

#     df = df.dropna(subset=['stationId', 'timestampDate'])

#     exclude_cols = ['stationId', 'timestamp', 'timestampDate']
#     params = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]

#     if not params:
#         print("🔴 ERROR: No numeric parameters found.")
#         return

#     df = df.groupby(['stationId', 'timestampDate'], as_index=False)[params].mean()
#     df = df.sort_values(['stationId', 'timestampDate'])

#     def create_sequences(data, window_size):
#         return np.array([data[i:i + window_size] for i in range(len(data) - window_size)])

#     all_anomalies = []
#     stations = df['stationId'].unique()

#     for station in stations:
#         print(f"   Processing anomalies for station: {station}...")
#         station_df = df[df['stationId'] == station].copy()

#         if len(station_df) < WINDOW_SIZE * 2:
#             print(f"   ⏭️ Skipping {station}: not enough data.")
#             continue

#         scaler = MinMaxScaler(feature_range=(0, 1))
#         station_df[params] = scaler.fit_transform(station_df[params])

#         sequences = create_sequences(station_df[params].values, WINDOW_SIZE)
#         if sequences.shape[0] == 0:
#             continue

#         model = Sequential([
#             LSTM(64, activation='relu', input_shape=(WINDOW_SIZE, len(params)), return_sequences=False),
#             RepeatVector(WINDOW_SIZE),
#             LSTM(64, activation='relu', return_sequences=True),
#             TimeDistributed(Dense(len(params)))
#         ])
#         model.compile(optimizer='adam', loss='mae')

#         with warnings.catch_warnings():
#             warnings.simplefilter("ignore")
#             model.fit(sequences, sequences, epochs=20, batch_size=32, verbose=0)
#             X_pred = model.predict(sequences, verbose=0)

#         mae = np.mean(np.abs(X_pred - sequences), axis=1)
#         threshold = np.quantile(mae, 0.95)

#         for i in range(len(mae)):
#             if mae[i].mean() > threshold:
#                 anomaly_timestamp = station_df.iloc[i + WINDOW_SIZE - 1]['timestampDate']
#                 for param_idx, param in enumerate(params):
#                     if mae[i, param_idx] > threshold:
#                         all_anomalies.append({
#                             "stationId": station,
#                             "timestamp": anomaly_timestamp,
#                             "Parameter": param
#                         })

#     if not all_anomalies:
#         print("⚠️ No anomalies found.")
#         return

#     print("   Aggregating anomalies for heatmap...")
#     anomaly_df = pd.DataFrame(all_anomalies)
#     anomaly_df['date'] = anomaly_df['timestamp'].dt.strftime('%Y-%m-%d')

#     summary_data = anomaly_df.groupby(['stationId', 'Parameter'])['date'].agg(
#         Anomaly_Count='count',
#         Sample_Dates=lambda x: ', '.join(x.unique())
#     ).reset_index()

#     heatmap_values = summary_data.pivot(index='stationId', columns='Parameter', values='Anomaly_Count').fillna(0)
#     hover_text = summary_data.pivot(index='stationId', columns='Parameter', values='Sample_Dates').fillna("No anomalies")
#     heatmap_values = heatmap_values.sort_index()
#     hover_text = hover_text.reindex_like(heatmap_values)

#     custom_hover = []
#     for r_idx, row in enumerate(heatmap_values.index):
#         row_hover = []
#         for c_idx, col in enumerate(heatmap_values.columns):
#             count = heatmap_values.iloc[r_idx, c_idx]
#             dates = hover_text.iloc[r_idx, c_idx]
#             row_hover.append(f"<b>Parameter: {col}</b><br>Station ID: {row}<br>Anomalies: {count}<br>Dates: {dates}")
#         custom_hover.append(row_hover)

#     fig = go.Figure(data=go.Heatmap(
#         z=heatmap_values.values,
#         x=heatmap_values.columns.tolist(),
#         y=heatmap_values.index.astype(str).tolist(),
#         text=heatmap_values.values,
#         texttemplate="%{text:.0f}",
#         hovertext=custom_hover,
#         hoverinfo="text",
#         colorscale='Reds'
#     ))
#     fig.update_layout(
#         title="Anomaly Count per Parameter and Station",
#         xaxis_title="Parameter",
#         yaxis_title="Station ID",
#         height=max(600, len(heatmap_values.index) * 20),
#         xaxis=dict(tickangle=315),
#         yaxis=dict(type='category')
#     )

#     fig_dict = fig.to_dict()
#     if 'data' in fig_dict and len(fig_dict['data']) > 0:
#         trace = fig_dict['data'][0]
#         for key in ['x', 'y', 'z', 'text', 'hovertext']:
#             if key in trace:
#                 data_array = trace[key]
#                 if isinstance(data_array, np.ndarray):
#                     trace[key] = data_array.tolist()
#                 elif key in ['z', 'text', 'hovertext'] and isinstance(data_array, list):
#                     trace[key] = [
#                         [int(item) if isinstance(item, (np.integer, np.floating)) else str(item) for item in row]
#                         if isinstance(row, (list, np.ndarray)) else row
#                         for row in data_array
#                     ]

#     with open(OUTPUT_JSON, 'w') as f:
#         json.dump(fig_dict, f, indent=2)
#     print(f"✅ Saved anomaly heatmap to: {OUTPUT_JSON}")
#     print("--- Anomaly Detection Batch Job Complete ---")


# if __name__ == "__main__":
#     run_anomaly_detection()



# backend/models/anomaly_detection.py
# Uses Isolation Forest (sklearn) instead of LSTM Autoencoder
# Much lighter — no TensorFlow needed, runs fine in GitHub Actions free tier

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import plotly.graph_objects as go
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)
from db import read_sql

OUTPUT_JSON = os.path.join(BACKEND_DIR, "static/anomaly/anomaly_heatmap.json")
CONTAMINATION = 0.05  # expect ~5% anomalies


def run_anomaly_detection():
    print("--- Starting Anomaly Detection Batch Job (Isolation Forest) ---")
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)

    # 1. Load data
    try:
        df = read_sql("SELECT * FROM water_records")
        df['timestampDate'] = pd.to_datetime(df['timestampDate'], errors='coerce')
    except Exception as e:
        print(f"🔴 ERROR: Could not read from database: {e}")
        return

    df = df.dropna(subset=['stationId', 'timestampDate'])

    exclude_cols = ['stationId', 'timestamp', 'timestampDate']
    params = [c for c in df.columns if c not in exclude_cols
              and pd.api.types.is_numeric_dtype(df[c])]

    if not params:
        print("🔴 ERROR: No numeric parameters found.")
        return

    print(f"Parameters: {params}")

    all_anomalies = []
    stations = df['stationId'].unique()

    # 2. Run Isolation Forest per station
    for station in stations:
        print(f"   Processing station: {station}...")
        station_df = df[df['stationId'] == station].copy()
        station_df = station_df.dropna(subset=params)

        if len(station_df) < 10:
            print(f"   ⏭️ Skipping {station}: not enough data ({len(station_df)} rows).")
            continue

        # Run one model per parameter for per-parameter anomaly detection
        for param in params:
            param_data = station_df[[param]].dropna()
            if len(param_data) < 10:
                continue

            try:
                iso = IsolationForest(
                    contamination=CONTAMINATION,
                    random_state=42,
                    n_estimators=50  # keep light
                )
                labels = iso.fit_predict(param_data)
                # -1 = anomaly, 1 = normal
                anomaly_mask = labels == -1
                anomaly_rows = station_df.loc[param_data.index[anomaly_mask]]

                for _, row in anomaly_rows.iterrows():
                    all_anomalies.append({
                        "stationId": station,
                        "timestamp": row['timestampDate'],
                        "Parameter": param
                    })
            except Exception as e:
                print(f"   ⚠️ Error for {station}/{param}: {e}")

    if not all_anomalies:
        print("⚠️ No anomalies found.")
        # Save empty heatmap so the endpoint doesn't 404
        fig = go.Figure()
        fig.update_layout(title="No anomalies detected yet.")
        with open(OUTPUT_JSON, 'w') as f:
            json.dump(fig.to_dict(), f)
        return

    # 3. Build heatmap
    print(f"   Total anomalies found: {len(all_anomalies)}")
    anomaly_df = pd.DataFrame(all_anomalies)
    anomaly_df['date'] = pd.to_datetime(anomaly_df['timestamp']).dt.strftime('%Y-%m-%d')

    summary = anomaly_df.groupby(['stationId', 'Parameter'])['date'].agg(
        Anomaly_Count='count',
        Sample_Dates=lambda x: ', '.join(sorted(x.unique())[:5])  # limit dates shown
    ).reset_index()

    heatmap_values = summary.pivot(
        index='stationId', columns='Parameter', values='Anomaly_Count'
    ).fillna(0)
    hover_text = summary.pivot(
        index='stationId', columns='Parameter', values='Sample_Dates'
    ).fillna("No anomalies")

    heatmap_values = heatmap_values.sort_index()
    hover_text = hover_text.reindex_like(heatmap_values)

    custom_hover = []
    for r_idx, row_id in enumerate(heatmap_values.index):
        row_hover = []
        for c_idx, col in enumerate(heatmap_values.columns):
            count = heatmap_values.iloc[r_idx, c_idx]
            dates = hover_text.iloc[r_idx, c_idx]
            row_hover.append(
                f"<b>Parameter: {col}</b><br>"
                f"Station: {row_id}<br>"
                f"Anomalies: {int(count)}<br>"
                f"Dates: {dates}"
            )
        custom_hover.append(row_hover)

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_values.values.tolist(),
        x=heatmap_values.columns.tolist(),
        y=heatmap_values.index.astype(str).tolist(),
        text=[[int(v) for v in row] for row in heatmap_values.values.tolist()],
        texttemplate="%{text}",
        hovertext=custom_hover,
        hoverinfo="text",
        colorscale='Reds'
    ))

    fig.update_layout(
        title="Anomaly Count per Parameter and Station (Isolation Forest)",
        xaxis_title="Parameter",
        yaxis_title="Station ID",
        height=max(600, len(heatmap_values.index) * 20),
        xaxis=dict(tickangle=315),
        yaxis=dict(type='category')
    )

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(fig.to_dict(), f, indent=2)
    print(f"✅ Saved anomaly heatmap to: {OUTPUT_JSON}")
    print("--- Anomaly Detection Complete ---")


if __name__ == "__main__":
    run_anomaly_detection()
