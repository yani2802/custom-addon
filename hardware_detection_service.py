from flask import Flask, jsonify, request
import logging
import socket
import subprocess
import re
import platform
import json
import os
import time
from threading import Thread, Lock

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global state
state = {
    'devices': [],
    'scanning': False,
    'last_scan': None,
    'scan_lock': Lock()
}

def save_devices_to_file():
    """Save detected devices to a JSON file"""
    try:
        with open('detected_devices.json', 'w') as f:
            json.dump(state['devices'], f)
        logger.info(f"Saved {len(state['devices'])} devices to file")
    except Exception as e:
        logger.error(f"Error saving devices to file: {e}")

def load_devices_from_file():
    """Load detected devices from a JSON file"""
    try:
        if os.path.exists('detected_devices.json'):
            with open('detected_devices.json', 'r') as f:
                state['devices'] = json.load(f)
                logger.info(f"Loaded {len(state['devices'])} devices from file")
    except Exception as e:
        logger.error(f"Error loading devices from file: {e}")

def detect_usb_devices():
    """Detect USB devices connected to the server"""
    devices = []
    
    try:
        if platform.system() == 'Windows':
            # On Windows, use PowerShell to get USB devices
            cmd = "Get-PnpDevice -PresentOnly | Where-Object { $_.Class -match 'Printer|USB|HIDClass|Camera|Media|Bluetooth|Net' } | Select-Object FriendlyName, DeviceID, Class | ConvertTo-Json"
            output = subprocess.check_output(['powershell', '-Command', cmd], stderr=subprocess.STDOUT).decode('utf-8')
            
            # Parse JSON output
            try:
                device_list = json.loads(output)
                # Handle case where only one device is returned (not in a list)
                if not isinstance(device_list, list):
                    device_list = [device_list]
                    
                for device in device_list:
                    friendly_name = device.get('FriendlyName', 'Unknown Device')
                    device_id = device.get('DeviceID', '')
                    device_class = device.get('Class', '')
                    
                    # Determine device type based on class
                    device_type = 'other'
                    if 'Printer' in device_class:
                        device_type = 'printer'
                    elif 'Camera' in device_class or 'Camera' in friendly_name:
                        device_type = 'camera'
                    elif 'HID' in device_class and ('Scanner' in friendly_name or 'Scan' in friendly_name):
                        device_type = 'scanner'
                    elif 'Media' in device_class:
                        device_type = 'media'
                    
                    devices.append({
                        'name': friendly_name,
                        'device_id': device_id,
                        'type': device_type,
                        'class': device_class
                    })
            except json.JSONDecodeError as je:
                logger.error(f"JSON Decode Error: {je}")
                logger.error(f"Raw output: {output}")
        
        # TODO: Add detection for Linux and macOS
        elif platform.system() == 'Linux':
            # Linux USB device detection logic
            pass
        elif platform.system() == 'Darwin':  # macOS
            # macOS USB device detection logic
            pass
        
        return devices
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error detecting USB devices: {e}")
        return []

def scan_devices():
    """Perform a device scan in a thread-safe manner"""
    with state['scan_lock']:
        if state['scanning']:
            return False
        
        state['scanning'] = True
        try:
            devices = detect_usb_devices()
            state['devices'] = devices
            state['last_scan'] = time.time()
            save_devices_to_file()
            return True
        except Exception as e:
            logger.error(f"Device scan error: {e}")
            return False
        finally:
            state['scanning'] = False

@app.route('/scan', methods=['POST'])
def trigger_scan():
    """Endpoint to trigger a device scan"""
    result = scan_devices()
    return jsonify({
        'success': result,
        'message': 'Scan completed' if result else 'Scan failed'
    })

@app.route('/devices', methods=['GET'])
def get_devices():
    """Endpoint to retrieve detected devices"""
    return jsonify(state['devices'])

if __name__ == '__main__':
    # Load previously saved devices on startup
    load_devices_from_file()
    
    # Optional: Perform initial scan
    scan_devices()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
