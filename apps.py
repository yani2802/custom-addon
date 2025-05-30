from flask import Flask, jsonify, request
import subprocess
import threading
import time
import random
from datetime import datetime

app = Flask(__name__)

# Global variables to track scanning state
scanning_state = {
    'nfc': False,
    'rfid': False,
    'qr': False,
    'bluetooth': False,
    'palmvein': False
}

devices_found = {
    'nfc': [],
    'rfid': [],
    'qr': [],
    'bluetooth': [],
    'palmvein': []
}

def get_system_devices():
    """Get current system devices using PowerShell"""
    try:
        cmd = 'Get-PnpDevice | Where-Object {$_.Status -eq "OK"} | Select-Object Class, DeviceID, FriendlyName | ConvertTo-Json'
        result = subprocess.run(['powershell', '-Command', cmd], 
                              capture_output=True, text=True, shell=True)
        
        if result.returncode == 0 and result.stdout.strip():
            import json
            devices_data = json.loads(result.stdout)
            
            # Handle both single device and array of devices
            if isinstance(devices_data, dict):
                devices_data = [devices_data]
            
            devices = []
            for device in devices_data:
                device_info = {
                    'class': device.get('Class', 'Unknown'),
                    'device_id': device.get('DeviceID', 'Unknown'),
                    'name': device.get('FriendlyName', 'Unknown Device'),
                    'type': classify_device_type(device.get('DeviceID', ''))
                }
                devices.append(device_info)
            
            return devices
        else:
            return []
            
    except Exception as e:
        print(f"Error getting system devices: {e}")
        return []

def classify_device_type(device_id):
    """Classify device based on device ID"""
    if not device_id:
        return "unknown"
    
    device_id_upper = device_id.upper()
    
    if "VID_7985&PID_1001" in device_id_upper:
        return "palmvein_scanner"
    elif "VID_222A&PID_0001" in device_id_upper and "TOUCH" in device_id_upper:
        return "touch_screen"
    elif "BLUETOOTH" in device_id_upper or "BTH" in device_id_upper:
        return "bluetooth"
    elif "USB" in device_id_upper:
        return "usb_device"
    elif "HID" in device_id_upper:
        return "input_device"
    elif "NET" in device_id_upper:
        return "network_device"
    elif "MEDIA" in device_id_upper or "AUDIO" in device_id_upper:
        return "audio_device"
    else:
        return "other"

@app.route('/')
def index():
    return jsonify({
        "message": "Multi-Device Scanner API",
        "version": "2.0",
        "status": "running",
        "endpoints": {
            "GET /devices": "Get all devices",
            "POST /scan/<type>": "Start scanning (nfc, rfid, qr, bluetooth, palmvein)",
            "DELETE /scan/<type>": "Stop scanning",
            "POST /scan/all": "Start all scans",
            "DELETE /clear/<type>": "Clear found devices",
            "GET /status": "Get scanning status"
        },
        "supported_scanners": list(scanning_state.keys())
    })

@app.route('/devices', methods=['GET'])
def get_devices():
    """Get all devices including system devices and scanned devices"""
    system_devices = get_system_devices()
    
    # Count devices by type
    device_counts = {
        'system': len(system_devices),
        'scanned': sum(len(devices) for devices in devices_found.values())
    }
    
    return jsonify({
        "connected_count": device_counts['system'],
        "scanned_count": device_counts['scanned'],
        "devices": {
            "system_devices": system_devices,
            **devices_found
        },
        "last_scan": datetime.now().isoformat(),
        "scanning": scanning_state,
        "total_count": device_counts['system'] + device_counts['scanned'],
        "device_counts": device_counts
    })

@app.route('/scan/<device_type>', methods=['POST'])
def start_scan(device_type):
    """Start scanning for specific device type"""
    
    valid_types = ['nfc', 'rfid', 'qr', 'bluetooth', 'palmvein']
    if device_type not in valid_types:
        return jsonify({
            "error": f"Invalid device type. Use: {', '.join(valid_types)}",
            "valid_types": valid_types
        }), 400
    
    if scanning_state[device_type]:
        return jsonify({
            "message": f"{device_type.upper()} scan already running",
            "status": "already_running",
            "scanning": True
        }), 200
    
    # Start the appropriate scanner
    try:
        scanning_state[device_type] = True
        
        if device_type == 'nfc':
            threading.Thread(target=simulate_nfc_scan, daemon=True).start()
        elif device_type == 'rfid':
            threading.Thread(target=simulate_rfid_scan, daemon=True).start()
        elif device_type == 'qr':
            threading.Thread(target=simulate_qr_scan, daemon=True).start()
        elif device_type == 'bluetooth':
            threading.Thread(target=simulate_bluetooth_scan, daemon=True).start()
        elif device_type == 'palmvein':
            threading.Thread(target=simulate_palmvein_scan, daemon=True).start()
        
        return jsonify({
            "message": f"{device_type.upper()} scan started successfully",
            "status": "started",
            "scanning": True,
            "device_type": device_type
        })
        
    except Exception as e:
        scanning_state[device_type] = False
        return jsonify({
            "error": f"{device_type.upper()} scan failed: {str(e)}",
            "status": "failed",
            "scanning": False
        }), 500

@app.route('/scan/<device_type>', methods=['DELETE'])
def stop_scan(device_type):
    """Stop scanning for specific device type"""
    
    if device_type not in scanning_state:
        return jsonify({
            "error": "Invalid device type",
            "valid_types": list(scanning_state.keys())
        }), 400
    
    was_scanning = scanning_state[device_type]
    scanning_state[device_type] = False
    
    return jsonify({
        "message": f"{device_type.upper()} scan stopped",
        "status": "stopped",
        "was_scanning": was_scanning,
        "scanning": False
    })

@app.route('/scan/all', methods=['POST'])
def start_all_scans():
    """Start all available scanners"""
    results = {}
    
    for device_type in scanning_state.keys():
        if not scanning_state[device_type]:
            try:
                scanning_state[device_type] = True
                
                if device_type == 'nfc':
                    threading.Thread(target=simulate_nfc_scan, daemon=True).start()
                elif device_type == 'rfid':
                    threading.Thread(target=simulate_rfid_scan, daemon=True).start()
                elif device_type == 'qr':
                    threading.Thread(target=simulate_qr_scan, daemon=True).start()
                elif device_type == 'bluetooth':
                    threading.Thread(target=simulate_bluetooth_scan, daemon=True).start()
                elif device_type == 'palmvein':
                    threading.Thread(target=simulate_palmvein_scan, daemon=True).start()
                
                results[device_type] = "started"
            except Exception as e:
                scanning_state[device_type] = False
                results[device_type] = f"failed: {str(e)}"
        else:
            results[device_type] = "already running"
    
    return jsonify({
        "message": "All scans initiated",
        "status": results
    })

@app.route('/status', methods=['GET'])
def get_status():
    """Get current scanning status"""
    return jsonify({
        "scanning_status": scanning_state,
        "active_scans": [k for k, v in scanning_state.items() if v],
        "device_counts": {k: len(v) for k, v in devices_found.items()},
        "timestamp": datetime.now().isoformat()
    })

@app.route('/clear/<device_type>', methods=['DELETE'])
def clear_devices(device_type):
    """Clear found devices for specific type"""
    
    if device_type == 'all':
        cleared_count = sum(len(devices) for devices in devices_found.values())
        for key in devices_found:
            devices_found[key] = []
        return jsonify({
            "message": "All scanned devices cleared",
            "cleared_count": cleared_count
        })
    
    if device_type in devices_found:
        cleared_count = len(devices_found[device_type])
        devices_found[device_type] = []
        return jsonify({
            "message": f"{device_type.upper()} devices cleared",
            "cleared_count": cleared_count
        })
    
    return jsonify({
        "error": "Invalid device type",
        "valid_types": list(devices_found.keys())
    }), 400

# Simulation functions for testing
def simulate_nfc_scan():
    """Simulate NFC tag detection"""
    print("🔍 NFC scanner started...")
    while scanning_state['nfc']:
        time.sleep(2)
        
        if random.random() < 0.3:  # 30% chance
            nfc_tag = {
                "id": f"nfc_{len(devices_found['nfc']) + 1}",
                "uid": f"04:{random.randint(10,99):02X}:{random.randint(10,99):02X}:{random.randint(10,99):02X}",
                "type": "NFC_TAG",
                "data": f"NFC Data {random.randint(1000, 9999)}",
                "timestamp": datetime.now().isoformat()
            }
            devices_found['nfc'].append(nfc_tag)
            print(f"📱 NFC tag detected: {nfc_tag['uid']}")

def simulate_rfid_scan():
    """Simulate RFID tag detection"""
    print("🔍 RFID scanner started...")
    while scanning_state['rfid']:
        time.sleep(3)
        
        if random.random() < 0.25:
            rfid_tag = {
                "id": f"rfid_{len(devices_found['rfid']) + 1}",
                "uid": f"{random.randint(100000000, 999999999)}",
                "type": "RFID_TAG",
                "data": f"RFID Card {random.randint(1000, 9999)}",
                "timestamp": datetime.now().isoformat()
            }
            devices_found['rfid'].append(rfid_tag)
            print(f"💳 RFID tag detected: {rfid_tag['uid']}")

def simulate_qr_scan():
    """Simulate QR code detection"""
    print("🔍 QR scanner started...")
    while scanning_state['qr']:
        time.sleep(1.5)
        
        if random.random() < 0.4:
            qr_code = {
                "id": f"qr_{len(devices_found['qr']) + 1}",
                "data": f"https://example.com/qr/{random.randint(1000, 9999)}",
                "type": "QR_CODE",
                "format": "QR_CODE",
                "timestamp": datetime.now().isoformat()
            }
            devices_found['qr'].append(qr_code)
            print(f"📷 QR code detected: {qr_code['data']}")

def simulate_bluetooth_scan():
    """Simulate Bluetooth device detection"""
    print("🔍 Bluetooth scanner started...")
    while scanning_state['bluetooth']:
        time.sleep(4)
        
        if random.random() < 0.2:
            bt_device = {
                "id": f"bt_{len(devices_found['bluetooth']) + 1}",
                "name": f"BT_Device_{random.randint(100, 999)}",
                "address": f"{random.randint(10,99):02X}:{random.randint(10,99):02X}:{random.randint(10,99):02X}:{random.randint(10,99):02X}:{random.randint(10,99):02X}:{random.randint(10,99):02X}",
                "type": "BLUETOOTH",
                "timestamp": datetime.now().isoformat()
            }
            devices_found['bluetooth'].append(bt_device)
            print(f"📡 Bluetooth device detected: {bt_device['name']}")

def simulate_palmvein_scan():
    """Simulate Palm Vein scanner (for your SaintDeem device)"""
    print("🔍 Palm Vein scanner started...")
    while scanning_state['palmvein']:
        time.sleep(5)
        
        if random.random() < 0.15:
            palm_scan = {
                "id": f"palm_{len(devices_found['palmvein']) + 1}",
                "template_id": f"PALM_{random.randint(10000, 99999)}",
                "type": "PALM_VEIN",
                "confidence": random.randint(85, 99),
                "device": "SaintDeem PalmVein Scanner",
                "timestamp": datetime.now().isoformat()
            }
            devices_found['palmvein'].append(palm_scan)
            print(f"🖐️ Palm vein detected: {palm_scan['template_id']} (confidence: {palm_scan['confidence']}%)")

if __name__ == '__main__':
    print("🚀 Starting Multi-Device Scanner API...")
    print("📡 Supported devices: NFC, RFID, QR Code, Bluetooth, Palm Vein")
    print("🌐 Server running on http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5001)
