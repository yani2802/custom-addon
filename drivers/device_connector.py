import asyncio
import logging
import socket
import time
from typing import Dict, Optional, Any
from ip_driver import NetworkScanner, NetworkDevice, NetworkDeviceType

_logger = logging.getLogger(__name__)

class DeviceConnector:
    """Handles actual device connections and communication"""
    
    def __init__(self):
        self.connected_devices: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    def connect_device(self, ip_address: str, device_type: str) -> bool:
        """Connect to a specific device"""
        try:
            if device_type == 'barcode_scanner':
                return self._connect_barcode_scanner(ip_address)
            elif device_type == 'nfc_reader':
                return self._connect_nfc_reader(ip_address)
            elif device_type == 'qr_scanner':
                return self._connect_qr_scanner(ip_address)
            elif device_type == 'printer':
                return self._connect_printer(ip_address)
            else:
                return self._connect_generic_device(ip_address)
                
        except Exception as e:
            self.logger.error(f"Error connecting to {device_type} at {ip_address}: {e}")
            return False
    
    def _connect_barcode_scanner(self, ip_address: str) -> bool:
        """Connect to barcode scanner"""
        try:
            # Try common barcode scanner ports
            ports = [9100, 9101, 23]
            
            for port in ports:
                if self._test_tcp_connection(ip_address, port):
                    self.connected_devices[ip_address] = {
                        'type': 'barcode_scanner',
                        'port': port,
                        'connection': None,
                        'last_activity': time.time()
                    }
                    self.logger.info(f"Connected to barcode scanner at {ip_address}:{port}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to barcode scanner: {e}")
            return False
    
    def _connect_nfc_reader(self, ip_address: str) -> bool:
        """Connect to NFC reader"""
        try:
            # Try common NFC reader ports
            ports = [8080, 8081, 14443]
            
            for port in ports:
                if self._test_tcp_connection(ip_address, port):
                    self.connected_devices[ip_address] = {
                        'type': 'nfc_reader',
                        'port': port,
                        'connection': None,
                        'last_activity': time.time()
                    }
                    self.logger.info(f"Connected to NFC reader at {ip_address}:{port}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to NFC reader: {e}")
            return False
    
    def _connect_qr_scanner(self, ip_address: str) -> bool:
        """Connect to QR scanner"""
        try:
            # Try common QR scanner ports
            ports = [9200, 9201, 8080]
            
            for port in ports:
                if self._test_tcp_connection(ip_address, port):
                    self.connected_devices[ip_address] = {
                        'type': 'qr_scanner',
                        'port': port,
                        'connection': None,
                        'last_activity': time.time()
                    }
                    self.logger.info(f"Connected to QR scanner at {ip_address}:{port}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to QR scanner: {e}")
            return False
    
    def _connect_printer(self, ip_address: str) -> bool:
        """Connect to printer"""
        try:
            # Try common printer ports
            ports = [9100, 631, 515]
            
            for port in ports:
                if self._test_tcp_connection(ip_address, port):
                    self.connected_devices[ip_address] = {
                        'type': 'printer',
                        'port': port,
                        'connection': None,
                        'last_activity': time.time()
                    }
                    self.logger.info(f"Connected to printer at {ip_address}:{port}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to printer: {e}")
            return False
    
    def _connect_generic_device(self, ip_address: str) -> bool:
        """Connect to generic device"""
        try:
            # Try common ports
            ports = [80, 8080, 23, 22]
            
            for port in ports:
                if self._test_tcp_connection(ip_address, port):
                    self.connected_devices[ip_address] = {
                        'type': 'generic',
                        'port': port,
                        'connection': None,
                        'last_activity': time.time()
                    }
                    self.logger.info(f"Connected to generic device at {ip_address}:{port}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to generic device: {e}")
            return False
    
   
    
    def disconnect_device(self, ip_address: str) -> bool:
        """Disconnect from device"""
        try:
            if ip_address in self.connected_devices:
                device_info = self.connected_devices[ip_address]
                if device_info.get('connection'):
                    device_info['connection'].close()
                    del self.connected_devices[ip_address]
                    self.logger.info(f"Disconnected from {device_info['type']} at {ip_address}:{device_info['port']}")
                    return True