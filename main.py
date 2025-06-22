# Read from serial and plot in real-time
import serial
import pandas as pd
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pytz

ser = serial.Serial('/dev/cu.usbserial-210', 115200)

# Field names for OPENLOG lines
openlog_fields = [
    "UTCDateTime","mac_address","firmware_ver","hardware","current_temp_f","current_humidity",
    "current_dewpoint_f","pressure","adc","mem","rssi","uptime","pm1_0_cf_1","pm2_5_cf_1",
    "pm10_0_cf_1","pm1_0_atm","pm2_5_atm","pm10_0_atm","pm2.5_aqi_cf_1","pm2.5_aqi_atm",
    "p_0_3_um","p_0_5_um","p_1_0_um","p_2_5_um","p_5_0_um","p_10_0_um","pm1_0_cf_1_b",
    "pm2_5_cf_1_b","pm10_0_cf_1_b","pm1_0_atm_b","pm2_5_atm_b","pm10_0_atm_b",
    "pm2.5_aqi_cf_1_b","pm2.5_aqi_atm_b","p_0_3_um_b","p_0_5_um_b","p_1_0_um_b",
    "p_2_5_um_b","p_5_0_um_b","p_10_0_um_b","gas"
]

openlog_rows = []
channel_rows = []

openlog_last_save = time.time()
channel_last_save = time.time()

print("Collecting data... Press Ctrl+C to stop.")

def fixNullValues(data):
  if len(data) != 41:
    data.append("0")
  elif len(data) == 41:
    return data
  
  if len(data) != 41:
    data.insert(8, '0')
  elif len(data) == 41:
    return data

  if len(data) != 41:
    data.insert(10, '0')
  elif len(data) == 41:
    return data
  return data

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
plt.ion()
plt.figure()  # <-- Add this line

try:
    while True:
        line = ser.readline().decode('utf-8').strip()
        if not line:
            continue
        line = str(line)
        if "OPENLOG" in line:
            data = line.split(",")
            data = fixNullValues(data)
            if len(openlog_fields) != len(data):
                continue
            else:  
                openlog_rows.append(dict(zip(openlog_fields, data)))
                print(f"OPENLOG row added: {openlog_rows[-1]}")
                if len(openlog_rows) > 1:
                    plot_realtime(openlog_rows)


        # Handle channel data (every second)
        # elif 'DATA' in line:
        #     try:
        #         # Example: .0h07:54.763 2025/06/22T12:21:11z: DATA A(4),82,38,54,1018.77,...
        #         parts = line.split()
        #         dateTime_UTC = None
        #         channel = None
        #         values = None
        #         for part in parts:
        #             if part.endswith('z:'):
        #                 dateTime_UTC = part[:-1]
        #         if 'DATA' in line:
        #             data_part = line.split('DATA', 1)[1].strip()
        #             if ',' in data_part:
        #                 channel, values_str = data_part.split(',', 1)
        #                 values = values_str.split(',')
        #         if dateTime_UTC and channel and values:
        #             channel_rows.append({
        #                 "dateTime_UTC": dateTime_UTC,
        #                 "channel": channel,
        #                 "value": values
        #             })
        #             print(f"Channel row added: {channel_rows[-1]}")
        #     except Exception as e:
        #         print(f"Error parsing channel data: {e}")

        # Save OPENLOG data every 3 minutes
        if time.time() - openlog_last_save > 180 and openlog_rows:
            df_openlog = pd.DataFrame(openlog_rows)
            df_openlog.to_csv("openlog_data.csv", index=False)
            print(f"Saved OPENLOG data ({len(openlog_rows)} rows) to openlog_data.csv")
            openlog_rows.clear()
            openlog_last_save = time.time()

        # Save channel data every 1 minute
        # if time.time() - channel_last_save > 60 and channel_rows:
        #     df_channel = pd.DataFrame(channel_rows)
        #     df_channel.to_csv("channel_data.csv", index=False)
        #     print(f"Saved channel data ({len(channel_rows)} rows) to channel_data.csv")
        #     channel_rows.clear()
        #     channel_last_save = time.time()

except KeyboardInterrupt:
    print("Stopping collection...")

# Final save on exit
if openlog_rows:
    pd.DataFrame(openlog_rows).to_csv("openlog_data.csv", index=False)
if channel_rows:
    pd.DataFrame(channel_rows).to_csv("channel_data.csv", index=False)
print("Final data saved.")
plt.show()