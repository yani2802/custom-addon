import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

try:
    import bleak
    from bleak import BleakScanner, BleakClient
    from bleak.backends.device import BLEDevice
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    BLEDevice = None

try:
    import bluetooth
    PYBLUEZ_AVAILABLE = True
except ImportError:
    PYBLUEZ_AVAILABLE = False

from config import Config

class BluetoothDeviceType(Enum):
    BARCODE_SCANNER = "barcode_scanner"
    NFC_READER = "nfc_reader"
    QR_SCANNER = "qr_scanner"
    PRINTER = "printer"
    CAMERA = "camera"
    UNKNOWN = "unknown"

@dataclass
class BluetoothDevice:
    address: str
    name: str
    device_type: BluetoothDeviceType
    rssi: Optional[int] = None
    is_connected: bool = False
    last_seen: float = 0
    connection_attempts: int = 0
    client: Optional[Any] = None
    services: List[str] = None
    manufacturer_data: Dict[int, bytes] = None
    
    def __post_init__(self):
        if self.services is None:
            self.services = []
        if self.manufacturer_data is None:
            self.manufacturer_data = {}
        self.last_seen = time.time()

class BluetoothManager:
    def __init__(self, config: Config, device_callback: Optional[Callable] = None):
        self.config = config
        self.device_callback = device_callback
        self.logger = logging.getLogger(__name__)
        
        # Device tracking
        self.discovered_devices: Dict[str, BluetoothDevice] = {}
        self.connected_devices: Dict[str, BluetoothDevice] = {}
        
        # Scanning state
        self.is_scanning = False
        self.scan_task = None
        self.connection_tasks: Dict[str, asyncio.Task] = {}
        
        # Check available Bluetooth libraries
        self.ble_available = BLEAK_AVAILABLE
        self.classic_available = PYBLUEZ_AVAILABLE
        
        if not (self.ble_available or self.classic_available):
            self.logger.warning("No Bluetooth libraries available. Install 'bleak' for BLE or 'pybluez' for classic Bluetooth")
    
    def _identify_device_type(self, name: str, manufacturer_data: Dict = None) -> BluetoothDeviceType:
        """Identify device type based on name and manufacturer data"""
        if not name:
            return BluetoothDeviceType.UNKNOWN
        
        name_lower = name.lower()
        
        # Check against supported device configurations
        for device_type, device_config in self.config.SUPPORTED_DEVICES.items():
            bluetooth_names = [n.lower() for n in device_config.get('bluetooth_names', [])]
            
            for bt_name in bluetooth_names:
                if bt_name in name_lower:
                    return BluetoothDeviceType(device_type)
        
        # Additional heuristics based on common device names
        if any(keyword in name_lower for keyword in ['scanner', 'barcode', 'symbol', 'honeywell', 'zebra']):
            return BluetoothDeviceType.BARCODE_SCANNER
        elif any(keyword in name_lower for keyword in ['nfc', 'rfid', 'acs', 'scm']):
            return BluetoothDeviceType.NFC_READER
        elif any(keyword in name_lower for keyword in ['qr', 'camera']):
            return BluetoothDeviceType.QR_SCANNER
        elif any(keyword in name_lower for keyword in ['printer', 'print']):
            return BluetoothDeviceType.PRINTER
        elif any(keyword in name_lower for keyword in ['camera', 'webcam', 'cam']):
            return BluetoothDeviceType.CAMERA
        
        return BluetoothDeviceType.UNKNOWN
    
    def _is_device_allowed(self, address: str) -> bool:
        """Check if device is allowed based on MAC address whitelist"""
        if not self.config.ALLOWED_DEVICE_MACS:
            return True  # Empty list means allow all
        return address.upper() in [mac.upper() for mac in self.config.ALLOWED_DEVICE_MACS]
    
    async def _handle_device_discovery(self, device: BLEDevice, advertisement_data=None):
        """Handle discovered BLE device"""
        try:
            address = device.address
            name = device.name or "Unknown Device"
            rssi = getattr(device, 'rssi', None)
            
            # Check if device is allowed
            if not self._is_device_allowed(address):
                self.logger.debug(f"Device {address} not in allowed list, skipping")
                return
            
            # Extract manufacturer data if available
            manufacturer_data = {}
            if advertisement_data and hasattr(advertisement_data, 'manufacturer_data'):
                manufacturer_data = advertisement_data.manufacturer_data
            
            # Identify device type
            device_type = self._identify_device_type(name, manufacturer_data)
            
            # Skip unknown devices if not configured to detect them
            if device_type == BluetoothDeviceType.UNKNOWN:
                self.logger.debug(f"Unknown device type for {name} ({address}), skipping")
                return
            
            # Create or update device record
            if address in self.discovered_devices:
                bt_device = self.discovered_devices[address]
                bt_device.last_seen = time.time()
                bt_device.rssi = rssi
                if manufacturer_data:
                    bt_device.manufacturer_data.update(manufacturer_data)
            else:
                bt_device = BluetoothDevice(
                    address=address,
                    name=name,
                    device_type=device_type,
                    rssi=rssi,
                    manufacturer_data=manufacturer_data
                )
                self.discovered_devices[address] = bt_device
                
                self.logger.info(f"Discovered Bluetooth device: {name} ({address}) - Type: {device_type.value}")
                
                # Notify callback about new device
                if self.device_callback:
                    await self._safe_callback(bt_device, 'discovered')
                
                # Auto-connect if enabled
                if self.config.AUTO_CONNECT_DEVICES and address not in self.connection_tasks:
                    self.connection_tasks[address] = asyncio.create_task(
                        self._connect_to_device(bt_device)
                    )
        
        except Exception as e:
            self.logger.error(f"Error handling device discovery: {e}")
    
    async def _connect_to_device(self, device: BluetoothDevice) -> bool:
        """Attempt to connect to a Bluetooth device"""
        try:
            if not self.ble_available:
                self.logger.warning("BLE not available for connection")
                return False
            
            self.logger.info(f"Attempting to connect to {device.name} ({device.address})")
            
            client = BleakClient(device.address)
            
            # Set connection timeout
            timeout = self.config.DEVICE_TIMEOUT
            
            try:
                connected = await asyncio.wait_for(client.connect(), timeout=timeout)
                
                if connected:
                    device.is_connected = True
                    device.client = client
                    device.connection_attempts = 0
                    self.connected_devices[device.address] = device
                    
                    # Discover services
                    try:
                        services = await client.get_services()
                        device.services = [str(service.uuid) for service in services]
                        self.logger.info(f"Connected to {device.name}, discovered {len(device.services)} services")
                    except Exception as e:
                        self.logger.warning(f"Could not discover services for {device.name}: {e}")
                    
                    # Notify callback about connection
                    if self.device_callback:
                        await self._safe_callback(device, 'connected')
                    
                    return True
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Connection timeout for {device.name}")
            except Exception as e:
                self.logger.error(f"Connection error for {device.name}: {e}")
            
            device.connection_attempts += 1
            
            # Check if we should stop trying to connect
            if device.connection_attempts >= self.config.MAX_RECONNECT_ATTEMPTS:
                self.logger.warning(f"Max connection attempts reached for {device.name}")
                return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to device {device.address}: {e}")
            return False
        finally:
            # Clean up connection task
            if device.address in self.connection_tasks:
                del self.connection_tasks[device.address]
    
    async def _disconnect_device(self, device: BluetoothDevice):
        """Disconnect from a Bluetooth device"""
        try:
            if device.client and device.is_connected:
                await device.client.disconnect()
                self.logger.info(f"Disconnected from {device.name}")
            
            device.is_connected = False
            device.client = None
            
            if device.address in self.connected_devices:
                del self.connected_devices[device.address]
            
            # Notify callback about disconnection
            if self.device_callback:
                await self._safe_callback(device, 'disconnected')
                
        except Exception as e:
            self.logger.error(f"Error disconnecting from {device.name}: {e}")
    
    async def _safe_callback(self, device: BluetoothDevice, event: str):
        """Safely call the device callback"""
        try:
            if asyncio.iscoroutinefunction(self.device_callback):
                await self.device_callback(device, event)
            else:
                self.device_callback(device, event)
        except Exception as e:
            self.logger.error(f"Error in device callback: {e}")
    
    async def start_scanning(self):
        """Start Bluetooth device scanning"""
        if not self.config.ENABLE_BLUETOOTH_DETECTION:
            self.logger.info("Bluetooth detection disabled in config")
            return
        
        if not self.ble_available:
            self.logger.warning("Bluetooth scanning not available - install 'bleak' library")
            return
        
        if self.is_scanning:
            self.logger.warning("Bluetooth scanning already active")
            return
        
        self.is_scanning = True
        self.logger.info("Starting Bluetooth device scanning")
        
        try:
            # Start continuous scanning
            scanner = BleakScanner()
            scanner.register_detection_callback(self._handle_device_discovery)
            
            await scanner.start()
            self.logger.info("Bluetooth scanner started")
            
            # Keep scanning until stopped
            while self.is_scanning:
                await asyncio.sleep(1)
            
            await scanner.stop()
            self.logger.info("Bluetooth scanner stopped")
            
        except Exception as e:
            self.logger.error(f"Error during Bluetooth scanning: {e}")
            self.is_scanning = False
    
    async def stop_scanning(self):
        """Stop Bluetooth device scanning"""
        self.logger.info("Stopping Bluetooth scanning")
        self.is_scanning = False
        
        # Cancel all connection tasks
        for task in self.connection_tasks.values():
            if not task.done():
                task.cancel()
        self.connection_tasks.clear()
        
        # Disconnect all devices
        for device in list(self.connected_devices.values()):
            await self._disconnect_device(device)
    
    async def scan_once(self) -> List[BluetoothDevice]:
        """Perform a single Bluetooth scan"""
        if not self.ble_available:
            self.logger.warning("Bluetooth scanning not available")
            return []
        
        try:
            self.logger.info("Performing single Bluetooth scan")
            
            devices = await BleakScanner.discover(timeout=self.config.BLUETOOTH_SCAN_DURATION)
            discovered = []
            
            for device in devices:
                await self._handle_device_discovery(device)
                if device.address in self.discovered_devices:
                    discovered.append(self.discovered_devices[device.address])
            
            self.logger.info(f"Single scan completed, found {len(discovered)} devices")
            return discovered
            
        except Exception as e:
            self.logger.error(f"Error during single Bluetooth scan: {e}")
            return []
    
    def get_discovered_devices(self) -> List[BluetoothDevice]:
        """Get list of all discovered devices"""
        return list(self.discovered_devices.values())
    
    def get_connected_devices(self) -> List[BluetoothDevice]:
        """Get list of connected devices"""
        return list(self.connected_devices.values())
    
    def get_device_by_address(self, address: str) -> Optional[BluetoothDevice]:
        """Get device by Bluetooth address"""
        return self.discovered_devices.get(address)
    
    async def connect_device(self, address: str) -> bool:
        """Manually connect to a device by address"""
        device = self.get_device_by_address(address)
        if not device:
            self.logger.error(f"Device {address} not found")
            return False
        
        if device.is_connected:
            self.logger.info(f"Device {address} already connected")
            return True
        
        return await self._connect_to_device(device)
    
    async def disconnect_device(self, address: str) -> bool:
        """Manually disconnect from a device by address"""
        device = self.get_device_by_address(address)
        if not device:
            self.logger.error(f"Device {address} not found")
            return False
        
        if not device.is_connected:
            self.logger.info(f"Device {address} not connected")
            return True
        
        await self._disconnect_device(device)
        return True
    
    def cleanup_old_devices(self, max_age_seconds: int = 300):
        """Remove devices that haven't been seen recently"""
        current_time = time.time()
        to_remove = []
        
        for address, device in self.discovered_devices.items():
            if current_time - device.last_seen > max_age_seconds:
                to_remove.append(address)
        
        for address in to_remove:
            device = self.discovered_devices.pop(address)
            self.logger.info(f"Removed old device: {device.name} ({address})")
    
    def get_device_info(self, address: str) -> Dict[str, Any]:
        """Get detailed information about a device"""
        device = self.get_device_by_address(address)
        if not device:
            return {}
        
        return {
            'address': device.address,
            'name': device.name,
            'device_type': device.device_type.value,
            'rssi': device.rssi,
            'is_connected': device.is_connected,
            'last_seen': device.last_seen,
            'connection_attempts': device.connection_attempts,
            'services': device.services,
            'manufacturer_data': {k: v.hex() for k, v in device.manufacturer_data.items()},
            'age_seconds': time.time() - device.last_seen
        }

# Example usage and testing
async def main():
    """Example usage of BluetoothManager"""
    config = Config()
    
    def device_callback(device: BluetoothDevice, event: str):
        print(f"Device {event}: {device.name} ({device.address}) - Type: {device.device_type.value}")
    
    bt_manager = BluetoothManager(config, device_callback)
    
    try:
        # Start scanning
        scan_task = asyncio.create_task(bt_manager.start_scanning())
        
        # Let it run for a while
        await asyncio.sleep(30)
        
        # Print discovered devices
        devices = bt_manager.get_discovered_devices()
        print(f"\nDiscovered {len(devices)} devices:")
        for device in devices:
            info = bt_manager.get_device_info(device.address)
            print(f"  {info}")
        
        # Stop scanning
        await bt_manager.stop_scanning()
        
    except KeyboardInterrupt:
        print("Stopping...")
        await bt_manager.stop_scanning()

if __name__ == "__main__":
    asyncio.run(main())