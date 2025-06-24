import pyqtgraph as pg
import pandas as pd
import sys
from pyqtgraph.Qt import QtWidgets, QtCore
from datetime import datetime
import pytz
import serial
import time
import os
import threading
import queue

SERIAL_PORT = '/dev/cu.usbserial-110'
BAUD_RATE = 115200
CSV_FILENAME = "openlog_data.csv"
SAVE_INTERVAL_SEC = 120  # 2 minutes
CHECK_INTERVAL_SEC = 180  # 3 minutes

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

def append_to_csv(dataframe, filename):
    file_exists = os.path.exists(filename)
    dataframe.to_csv(filename, mode='a', header=not file_exists, index=False)

class SerialReader(threading.Thread):
    def __init__(self, data_queue, stop_event):
        super().__init__(daemon=True)
        self.data_queue = data_queue
        self.stop_event = stop_event

    def run(self):
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print("Serial port opened.")
            while not self.stop_event.is_set():
                line = ser.readline().decode('utf-8').strip()
                if not line:
                    continue
                if "OPENLOG" in line:
                    data = line.split(",")
                    data = fixNullValues(data)
                    if len(openlog_fields) != len(data):
                        continue
                    row = dict(zip(openlog_fields, data))
                    print(row)
                    self.data_queue.put(row)
        except Exception as e:
            print("Serial thread error:", e)

class RealTimePlotter(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-time PM2.5 Data")
        date_axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': date_axis})
        self.setCentralWidget(self.plot_widget)
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='b', width=2),
            symbol='o', symbolSize=8,
            symbolBrush=(0, 0, 255), symbolPen='w',
            name='PM 2.5'  # This name is used by the legend
        )
        self.plot_widget.setLabel('left', "Concentration (µg/m³)", **{'color': '#FFF', 'font-size': '14pt'})
        self.plot_widget.setLabel('bottom', "Time (EST)", **{'color': '#FFF', 'font-size': '14pt'})
        pg.setConfigOptions(antialias=True)
        self.bottom_axis = self.plot_widget.getAxis('bottom')

        # Add legend
        legend = pg.LegendItem(offset=(50, 10))
        legend.setParentItem(self.plot_widget.graphicsItem())
        legend.setBrush('w')
        legend.addItem(self.curve, 'PM 2.5')

        self.x_data = []
        self.y_data = []
        self.openlog_rows = []
        self.last_save_time = time.time()
        self.last_data_time = time.time()
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.reader_thread = SerialReader(self.data_queue, self.stop_event)
        self.reader_thread.start()

        # Load existing CSV if present
        self.load_existing_csv()

        # Timer for periodic plot update and data check
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_from_queue)
        self.timer.start(1000)  # Check every second

    def load_existing_csv(self):
        try:
            df = pd.read_csv(CSV_FILENAME)
            df['UTCDateTime'] = pd.to_datetime(df['UTCDateTime'], errors='coerce', utc=True)
            df['ESTDateTime'] = df['UTCDateTime'].dt.tz_convert('US/Eastern')
            df['pm2_5_atm'] = pd.to_numeric(df['pm2_5_atm'], errors='coerce')
            self.x_data = df['ESTDateTime'].tolist()
            self.y_data = df['pm2_5_atm'].tolist()
            print(f"Loaded {len(self.x_data)} points from CSV.")
        except Exception as e:
            print("No File Found or error loading:", e)
            self.x_data = []
            self.y_data = []

    def update_from_queue(self):
        new_data = False
        while not self.data_queue.empty():
            row = self.data_queue.get()
            self.openlog_rows.append(row)
            try:
                utc_dt = pd.to_datetime(row['UTCDateTime'], errors='coerce', utc=True)
                est_dt = utc_dt.tz_convert('US/Eastern')
                pm25 = float(row['pm2_5_atm'])
                self.x_data.append(est_dt)
                self.y_data.append(pm25)
                new_data = True
                self.last_data_time = time.time()
            except Exception as e:
                print("Parse error:", e)

        # Save every 2 minutes if new data
        if time.time() - self.last_save_time > SAVE_INTERVAL_SEC and self.openlog_rows:
            df_openlog = pd.DataFrame(self.openlog_rows)
            append_to_csv(df_openlog, CSV_FILENAME)
            print(f"Saved {len(self.openlog_rows)} rows to {CSV_FILENAME}")
            self.openlog_rows.clear()
            self.last_save_time = time.time()

        # If no new data for 3 minutes, reload CSV and plot again
        if not new_data and (time.time() - self.last_data_time > CHECK_INTERVAL_SEC):
            print("No new data for 3 minutes, reloading CSV...")
            self.load_existing_csv()
            self.last_data_time = time.time()

        self.update_plot()

    def update_plot(self):
        x_float = [dt.timestamp() for dt in self.x_data]
        y_vals = self.y_data
        self.curve.setData(x=x_float, y=y_vals)
        ticks_primary = [(ts, datetime.fromtimestamp(ts).strftime("%m/%d\n%H:%M:%S")) for ts in x_float]
        self.bottom_axis.setTicks([ticks_primary])

    def closeEvent(self, event):
        self.stop_event.set()
        self.reader_thread.join()
        # Final save on exit
        if self.openlog_rows:
            df_openlog = pd.DataFrame(self.openlog_rows)
            append_to_csv(df_openlog, CSV_FILENAME)
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = RealTimePlotter()
    win.show()
    sys.exit(app.exec_())