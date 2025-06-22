import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import random
import time
import pytz

# Fields used in the original script
openlog_fields = [
    "UTCDateTime","mac_address","firmware_ver","hardware","current_temp_f","current_humidity",
    "current_dewpoint_f","pressure","adc","mem","rssi","uptime","pm1_0_cf_1","pm2_5_cf_1",
    "pm10_0_cf_1","pm1_0_atm","pm2_5_atm","pm10_0_atm","pm2.5_aqi_cf_1","pm2.5_aqi_atm",
    "p_0_3_um","p_0_5_um","p_1_0_um","p_2_5_um","p_5_0_um","p_10_0_um","pm1_0_cf_1_b",
    "pm2_5_cf_1_b","pm10_0_cf_1_b","pm1_0_atm_b","pm2_5_atm_b","pm10_0_atm_b",
    "pm2.5_aqi_cf_1_b","pm2.5_aqi_atm_b","p_0_3_um_b","p_0_5_um_b","p_1_0_um_b",
    "p_2_5_um_b","p_5_0_um_b","p_10_0_um_b","gas"
]

# Generate dummy data row
def generate_dummy_row(timestamp):
    row = [
        timestamp.isoformat(),        # UTCDateTime
        "AA:BB:CC:DD:EE:FF",          # mac_address
        "v1.0",                       # firmware_ver
        "revA",                       # hardware
        f"{random.uniform(60, 90):.1f}",  # current_temp_f
        f"{random.uniform(20, 60):.1f}",  # current_humidity
        f"{random.uniform(30, 50):.1f}",  # current_dewpoint_f
        f"{random.uniform(1000, 1020):.2f}",  # pressure
        "123", "456", "-70", "3600",        # adc, mem, rssi, uptime
        *[f"{random.uniform(1, 100):.1f}" for _ in range(27)],  # PM + AQI + bins
        "1.23"                             # gas
    ]
    return dict(zip(openlog_fields, row))

# Plot function (unchanged from your code)
def plot_realtime(openlog_rows):
    if not openlog_rows:
        return
    df = pd.DataFrame(openlog_rows)

    # Parse as UTC and convert to US/Eastern
    df['UTCDateTime'] = pd.to_datetime(df['UTCDateTime'], errors='coerce', utc=True)
    df['ESTDateTime'] = df['UTCDateTime'].dt.tz_convert('US/Eastern')

    for col in ['pm1_0_atm', 'pm2_5_atm', 'pm10_0_atm']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    plt.clf()
    plt.plot(df['ESTDateTime'], df['pm1_0_atm'], label='PM1.0 ATM', linestyle='-', marker='o', color="black")
    plt.plot(df['ESTDateTime'], df['pm2_5_atm'], label='PM2.5 ATM', linestyle='-', marker='s', color="red")
    plt.plot(df['ESTDateTime'], df['pm10_0_atm'], label='PM10.0 ATM', linestyle='-', marker='^', color="pink")

    plt.gcf().autofmt_xdate(rotation=30)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %d %H:%M'))
    plt.xlabel('Time (EST)')
    plt.ylabel('Concentration (µg/m³)')
    plt.legend()
    plt.title('Real-time PM Data')
    plt.pause(0.1)
# Run simulation
openlog_rows = []
start_time = datetime.now()

plt.ion()
plt.figure()

try:
    for i in range(50):  # simulate 50 data points
        timestamp = start_time + timedelta(seconds=i * 5)
        row = generate_dummy_row(timestamp)
        openlog_rows.append(row)
        print(f"Added dummy row {i+1}: {row['UTCDateTime']}")
        plot_realtime(openlog_rows)
        time.sleep(0.2)  # simulate short delay between readings

except KeyboardInterrupt:
    print("Simulation stopped.")

plt.ioff()
plt.show()
