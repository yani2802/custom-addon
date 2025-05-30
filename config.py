import os
import json
from pathlib import Path
import logging

class Config:
    def __init__(self):
        self.config_dir = Path.home() / '.hardware_agent'
        self.config_file = self.config_dir / 'config.json'
        self.log_dir = self.config_dir / 'logs'
        self.load_config()
        self.ensure_directories()
    
    def load_config(self):
        """Load configuration from file and environment"""
        # Default configuration
        self.API_SERVER_URL = "http://localhost:5000"
        self.SCAN_INTERVAL = 5  # seconds
        self.ENABLE_USB_DETECTION = True
        self.ENABLE_BLUETOOTH_DETECTION = True
        self.ENABLE_WIFI_DETECTION = True
        self.ENABLE_SYSTEM_TRAY = True
        self.LOG_LEVEL = "INFO"
        self.AUTO_CONNECT_DEVICES = True
        self.DEVICE_TIMEOUT = 30  # seconds
        self.MAX_RECONNECT_ATTEMPTS = 3
        self.HEARTBEAT_INTERVAL = 60  # seconds
        self.ENABLE_ENCRYPTION = True
        self.API_KEY = ""
        
        # Load from config file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    for key, value in file_config.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
            except Exception as e:
                print(f"Error loading config file: {e}")
        
        # Override with environment variables
        self.API_SERVER_URL = os.getenv('HARDWARE_API_SERVER_URL', self.API_SERVER_URL)
        self.SCAN_INTERVAL = int(os.getenv('HARDWARE_SCAN_INTERVAL', str(self.SCAN_INTERVAL)))
        self.LOG_LEVEL = os.getenv('HARDWARE_LOG_LEVEL', self.LOG_LEVEL)
        self.API_KEY = os.getenv('HARDWARE_API_KEY', self.API_KEY)
        
        # Supported device types with detailed configuration
        self.SUPPORTED_DEVICES = {
            'barcode_scanner': {
                'usb_vendors': ['0x05e0', '0x04b4', '0x0536', '0x1659'],  # Symbol, Honeywell, Hand Held Products, Zebra
                'usb_products': ['0x1900', '0x0001', '0x02bc'],
                'bluetooth_names': ['Scanner', 'Barcode', 'Symbol', 'Honeywell'],
                'wifi_ports': [9100, 9101, 23],
                'serial_baudrates': [9600, 115200, 38400],
                'protocols': ['HID', 'Serial', 'TCP']
            },
            'nfc_reader': {
                'usb_vendors': ['0x072f', '0x04e6', '0x0b97', '0x1fd3'],  # ACS, SCM, O2Micro, A3K
                'usb_products': ['0x2200', '0x5116', '0x7772'],
                'bluetooth_names': ['NFC', 'RFID', 'ACS', 'SCM'],
                'wifi_ports': [8080, 8081, 14443],
                'serial_baudrates': [9600, 115200],
                'protocols': ['PCSC', 'Serial', 'TCP']
            },
            'qr_scanner': {
                'usb_vendors': ['0x05e0', '0x1a86', '0x2341'],  # Symbol, QinHeng, Arduino
                'usb_products': ['0x1200', '0x7523', '0x0043'],
                'bluetooth_names': ['QR', 'Scanner', 'Camera'],
                'wifi_ports': [9200, 9201, 8080],
                'serial_baudrates': [9600, 115200],
                'protocols': ['HID', 'Serial', 'TCP', 'HTTP']
            },
            'printer': {
                'usb_vendors': ['0x04b8', '0x03f0', '0x04a9'],  # Epson, HP, Canon
                'usb_products': ['0x0005', '0x002a', '0x1234'],
                'bluetooth_names': ['Printer', 'Print'],
                'wifi_ports': [9100, 631, 515],
                'serial_baudrates': [9600, 19200],
                'protocols': ['IPP', 'LPR', 'RAW']
            },
            'camera': {
                'usb_vendors': ['0x046d', '0x0c45', '0x1e4e'],  # Logitech, Microdia, Cubeternet
                'usb_products': ['0x085b', '0x6001', '0x0110'],
                'bluetooth_names': ['Camera', 'Webcam'],
                'wifi_ports': [8080, 554, 1935],
                'serial_baudrates': [115200],
                'protocols': ['UVC', 'RTSP', 'HTTP']
            }
        }
        
        # Network scanning configuration
        self.NETWORK_SCAN_RANGE = "192.168.1.0/24"
        self.BLUETOOTH_SCAN_DURATION = 10  # seconds
        self.USB_POLL_INTERVAL = 2  # seconds
        
        # Security settings
        self.ALLOWED_DEVICE_MACS = []  # Empty means allow all
        self.REQUIRE_DEVICE_AUTHENTICATION = False
        
    def ensure_directories(self):
        """Create necessary directories"""
        self.config_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
    
    def save_config(self):
        """Save current configuration to file"""
        config_data = {
            'API_SERVER_URL': self.API_SERVER_URL,
            'SCAN_INTERVAL': self.SCAN_INTERVAL,
            'ENABLE_USB_DETECTION': self.ENABLE_USB_DETECTION,
            'ENABLE_BLUETOOTH_DETECTION': self.ENABLE_BLUETOOTH_DETECTION,
            'ENABLE_WIFI_DETECTION': self.ENABLE_WIFI_DETECTION,
            'ENABLE_SYSTEM_TRAY': self.ENABLE_SYSTEM_TRAY,
            'LOG_LEVEL': self.LOG_LEVEL,
            'AUTO_CONNECT_DEVICES': self.AUTO_CONNECT_DEVICES,
            'DEVICE_TIMEOUT': self.DEVICE_TIMEOUT,
            'MAX_RECONNECT_ATTEMPTS': self.MAX_RECONNECT_ATTEMPTS,
            'HEARTBEAT_INTERVAL': self.HEARTBEAT_INTERVAL,
            'ENABLE_ENCRYPTION': self.ENABLE_ENCRYPTION,
            'API_KEY': self.API_KEY,
            'NETWORK_SCAN_RANGE': self.NETWORK_SCAN_RANGE,
            'BLUETOOTH_SCAN_DURATION': self.BLUETOOTH_SCAN_DURATION,
            'USB_POLL_INTERVAL': self.USB_POLL_INTERVAL,
            'ALLOWED_DEVICE_MACS': self.ALLOWED_DEVICE_MACS,
            'REQUIRE_DEVICE_AUTHENTICATION': self.REQUIRE_DEVICE_AUTHENTICATION
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")