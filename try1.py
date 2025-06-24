import serial
import pandas as pd
import time
from datetime import datetime
import os

import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import plotly.graph_objs as go
import threading

# Serial setup
ser = serial.Serial('/dev/cu.usbserial-210', 115200)
openlog_fields = [
    "UTCDateTime","mac_address","firmware_ver","hardware","current_temp_f","current_humidity",
    "current_dewpoint_f","pressure","adc","mem","rssi","uptime","pm1_0_cf_1","pm2_5_cf_1",
    "pm10_0_cf_1","pm1_0_atm","pm2_5_atm","pm10_0_atm","pm2.5_aqi_cf_1","pm2.5_aqi_atm",
    "p_0_3_um","p_0_5_um","p_1_0_um","p_2_5_um","p_5_0_um","p_10_0_um","pm1_0_cf_1_b",
    "pm2_5_cf_1_b","pm10_0_cf_1_b","pm1_0_atm_b","pm2_5_atm_b","pm10_0_atm_b",
    "pm2.5_aqi_cf_1_b","pm2.5_aqi_atm_b","p_0_3_um_b","p_0_5_um_b","p_1_0_um_b",
    "p_2_5_um_b","p_5_0_um_b","p_10_0_um_b","gas"
]

def fixNullValues(data):
    if len(data) != 41:
        data.append("0")
    if len(data) != 41:
        data.insert(8, '0')
    if len(data) != 41:
        data.insert(10, '0')
    return data

# Shared DataFrame for real-time updates
csv_file = "openlog_data.csv"
if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
else:
    df = pd.DataFrame(columns=openlog_fields)

# Serial reading thread
def serial_thread():
    global df
    openlog_rows = []
    last_save = time.time()
    while True:
        line = ser.readline().decode('utf-8').strip()
        if not line or "OPENLOG" not in line:
            continue
        data = fixNullValues(line.split(","))
        if len(openlog_fields) != len(data):
            continue
        row = dict(zip(openlog_fields, data))
        openlog_rows.append(row)
        print("Added the row to the dataset.")
        
        # Save every 2 minutes
        if time.time() - last_save > 120 and openlog_rows:
            new_df = pd.DataFrame(openlog_rows)
            new_df.to_csv(csv_file, mode='a', header=not os.path.exists(csv_file), index=False)
            df = pd.concat([df, new_df], ignore_index=True)
            openlog_rows.clear()
            last_save = time.time()

# Start serial reading in background
threading.Thread(target=serial_thread, daemon=True).start()

# Dash app setup
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H2("Real-Time PM2.5 Data"),
    dcc.Graph(id='live-graph', animate=False),
    dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0)  # update every 1 min
])

@app.callback(
    Output('live-graph', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_graph_live(n):
    if os.path.exists(csv_file):
        data_df = pd.read_csv(csv_file)
        if "UTCDateTime" in data_df and "pm2_5_atm" in data_df:
            try:
                data_df = data_df.dropna(subset=["UTCDateTime", "pm2_5_atm"])
                data_df["UTCDateTime"] = pd.to_datetime(data_df["UTCDateTime"], format="%Y/%m/%dT%H:%M:%Sz")
                data_df["pm2_5_atm"] = pd.to_numeric(data_df["pm2_5_atm"], errors='coerce')
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=data_df["UTCDateTime"],
                    y=data_df["pm2_5_atm"],
                    mode='lines+markers',
                    name='PM2.5 (µg/m³)'
                ))
                fig.update_layout(
                    xaxis_title="Time (UTC)",
                    yaxis_title="PM2.5 (µg/m³)",
                    title="Real-Time PM2.5 Data",
                    template="plotly_white"
                )
                return fig
            except Exception as e:
                print("Plot error:", e)
    return go.Figure()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)