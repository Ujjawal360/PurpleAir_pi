import pandas as pd
from datetime import datetime
import dash
from dash import dcc, html
from dash.dependencies import Output, Input
import plotly.graph_objs as go
import os

csv_file = "openlog_data.csv"

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H2("Real-Time PM Data"),
    dcc.Graph(id='live-graph'),
    dcc.Interval(id='interval-component', interval=120*1000, n_intervals=0)  # update every 120 seconds
])

@app.callback(
    Output('live-graph', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_graph_live(n):
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        # Use correct column names as per your CSV
        cols = ["UTCDateTime", "pm1_0_atm", "pm2_5_atm", "pm10_0_atm"]
        if all(col in df for col in cols):
            try:
                df = df.dropna(subset=cols)
                df["UTCDateTime"] = pd.to_datetime(df["UTCDateTime"], format="%Y/%m/%dT%H:%M:%Sz", utc=True)
                df["ESTDateTime"] = df["UTCDateTime"].dt.tz_convert('US/Eastern')
                df["pm1_0_atm"] = pd.to_numeric(df["pm1_0_atm"], errors='coerce')
                df["pm2_5_atm"] = pd.to_numeric(df["pm2_5_atm"], errors='coerce')
                df["pm10_0_atm"] = pd.to_numeric(df["pm10_0_atm"], errors='coerce')
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df["ESTDateTime"],
                    y=df["pm1_0_atm"],
                    mode='lines+markers',
                    name='PM1.0 (µg/m³)',
                    line=dict(color='blue')
                ))
                fig.add_trace(go.Scatter(
                    x=df["ESTDateTime"],
                    y=df["pm2_5_atm"],
                    mode='lines+markers',
                    name='PM2.5 (µg/m³)',
                    line=dict(color='green')
                ))
                fig.add_trace(go.Scatter(
                    x=df["ESTDateTime"],
                    y=df["pm10_0_atm"],
                    mode='lines+markers',
                    name='PM10.0 (µg/m³)',
                    line=dict(color='red')
                ))
                fig.update_layout(
                    xaxis_title="Time (US/Eastern)",
                    yaxis_title="Concentration (µg/m³)",
                    title="Real-Time PM Concentration",
                    legend=dict(title="Legend")
                )
                return fig
            except Exception as e:
                print("Plot error:", e)
    return go.Figure()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)