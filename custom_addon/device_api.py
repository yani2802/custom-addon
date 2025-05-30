from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import datetime
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s: %(message)s')

class DeviceManager:
    def __init__(self, db_path='devices.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS devices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        mac_address TEXT UNIQUE,
                        ip_address TEXT,
                        status TEXT DEFAULT 'disconnected',
                        last_seen DATETIME
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")

    def get_all_devices(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM devices")
                devices = cursor.fetchall()
                
                device_list = [
                    {
                        "id": device[0],
                        "name": device[1],
                        "mac_address": device[2],
                        "ip_address": device[3],
                        "status": device[4],
                        "last_seen": device[5]
                    } for device in devices
                ]
                return device_list
        except sqlite3.Error as e:
            logging.error(f"Error fetching devices: {e}")
            return []

    def add_device(self, name, mac_address, ip_address):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO devices 
                    (name, mac_address, ip_address, status, last_seen) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, mac_address, ip_address, 'connected', datetime.datetime.now()))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error adding device: {e}")
            return False

device_manager = DeviceManager()

@app.route('/devices', methods=['GET'])
def get_devices():
    devices = device_manager.get_all_devices()
    return jsonify({
        "connected_count": len([d for d in devices if d['status'] == 'connected']),
        "devices": devices,
        "last_scan": datetime.datetime.now().isoformat(),
        "scanning": False,
        "total_count": len(devices)
    })

@app.route('/devices/add', methods=['POST'])
def add_device():
    data = request.json
    result = device_manager.add_device(
        data.get('name', 'Unknown Device'),
        data.get('mac_address'),
        data.get('ip_address')
    )
    return jsonify({"success": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
