# Read from serial and plot in real-time
import serial
import pandas as pd
import time
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pytz
import os

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
                file_exists = os.path.exists("openlog_data.csv")
                pd.DataFrame([openlog_rows[-1]]).to_csv(
                    "openlog_data.csv",
                    mode='a' if file_exists else 'w',
                    header=not file_exists,
                    index=False
                )
                openlog_rows.clear() 

        # Save OPENLOG data every 3 minutes
        # if time.time() - openlog_last_save > 180 and openlog_rows:
        #     file_exists = os.path.exists("openlog_data.csv")
        #     df_openlog = pd.DataFrame(openlog_rows)
        #     df_openlog.to_csv(
        #         "openlog_data.csv",
        #         mode='a' if file_exists else 'w',
        #         header=not file_exists,
        #         index=False
        #     )
        #     print(f"Saved OPENLOG data ({len(openlog_rows)} rows) to openlog_data.csv")
        #     openlog_rows.clear()
        #     openlog_last_save = time.time()


except KeyboardInterrupt:
    print("Stopping collection...")

# Final save on exit
# if openlog_rows:
#     file_exists = os.path.exists("./openlog_data.csv")
#     pd.DataFrame(openlog_rows).to_csv(
#         "openlog_data.csv",
#         mode='a' if file_exists else 'w',
#         header=not file_exists,
#         index=False
#     )
if channel_rows:
    pd.DataFrame(channel_rows).to_csv("channel_data.csv", index=False)
print("Final data saved.")
plt.show()