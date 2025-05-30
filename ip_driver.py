import asyncio
import socket
import logging
import time
import ipaddress
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import struct
import json

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import nmap
    NMAP_AVAILABLE = True
except ImportError:
    NMAP_AVAILABLE = False

from config import Config

class NetworkDeviceType(Enum):
    BARCODE_SCANNER = "barcode_scanner"
    NFC_READER = "nfc_reader"
    QR_SCANNER = "qr_scanner"
    PRINTER = "printer"
    CAMERA = "camera"
    UNKNOWN = "unknown"

class ConnectionProtocol(Enum):
    TCP = "tcp"
    UDP = "udp"
    HTTP = "http"
    HTTPS = "https"
    IPP = "ipp"
    LPR = "lpr"
    RAW = "raw"
    RTSP = "rtsp"

@dataclass
class NetworkDevice:
    ip_address: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    device_type: NetworkDeviceType = NetworkDeviceType.UNKNOWN
    open_ports: List[int] = None
    protocols: List[ConnectionProtocol] = None
    manufacturer: Optional[str] = None
    device_info: Dict[str, Any] = None
    is_connected: bool = False
    last_seen: float = 0
    connection_attempts: int = 0
    response_time: Optional[float] = None
    
    def __post_init__(self):
        if self.open_ports is None:
            self.open_ports = []
        if self.protocols is None:
            self.protocols = []
        if self.device_info is None:
            self.device_info = {}
        self.last_seen = time.time()

class NetworkScanner:
    def __init__(self, config: Config, device_callback: Optional[Callable] = None):
        self.config = config
        self.device_callback = device_callback
        self.logger = logging.getLogger(__name__)
        
        # Device tracking
        self.discovered_devices: Dict[str, NetworkDevice] = {}
        self.connected_devices: Dict[str, NetworkDevice] = {}
        
        # Scanning state
        self.is_scanning = False
        self.scan_task = None
        self.connection_tasks: Dict[str, asyncio.Task] = {}
        
        # Network configuration
        self.scan_network = ipaddress.IPv4Network(self.config.NETWORK_SCAN_RANGE, strict=False)
        
        # Check available libraries
        self.aiohttp_available = AIOHTTP_AVAILABLE
        self.nmap_available = NMAP_AVAILABLE
        
        if not self.aiohttp_available:
            self.logger.warning("aiohttp not available. Install with: pip install aiohttp")
    
    def _get_device_ports(self, device_type: NetworkDeviceType) -> List[int]:
        """Get expected ports for device type"""
        if device_type == NetworkDeviceType.UNKNOWN:
            return []
        
        device_config = self.config.SUPPORTED_DEVICES.get(device_type.value, {})
        return device_config.get('wifi_ports', [])
    
    def _identify_device_type(self, ip: str, open_ports: List[int], device_info: Dict = None) -> NetworkDeviceType:
        """Identify device type based on open ports and device information"""
        
        # Check each supported device type
        for device_type_str, device_config in self.config.SUPPORTED_DEVICES.items():
            expected_ports = device_config.get('wifi_ports', [])
            
            # Check if any expected ports are open
            if any(port in open_ports for port in expected_ports):
                return NetworkDeviceType(device_type_str)
        
        # Additional heuristics based on common ports
        if 9100 in open_ports or 631 in open_ports or 515 in open_ports:
            return NetworkDeviceType.PRINTER
        elif 8080 in open_ports or 554 in open_ports or 1935 in open_ports:
            return NetworkDeviceType.CAMERA
        elif any(port in open_ports for port in [9100, 9101, 9200, 9201]):
            return NetworkDeviceType.BARCODE_SCANNER
        
        return NetworkDeviceType.UNKNOWN
    
    async def _ping_host(self, ip: str) -> Tuple[bool, Optional[float]]:
        """Ping a host to check if it's alive"""
        try:
            # Use asyncio subprocess for ping
            if hasattr(asyncio, 'create_subprocess_exec'):
                process = await asyncio.create_subprocess_exec(
                    'ping', '-c', '1', '-W', '1000', ip,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                start_time = time.time()
                stdout, stderr = await process.communicate()
                response_time = time.time() - start_time
                
                if process.returncode == 0:
                    return True, response_time
            
            return False, None
            
        except Exception as e:
            self.logger.debug(f"Ping failed for {ip}: {e}")
            return False, None
    
    async def _scan_port(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        """Scan a single port on a host"""
        try:
            future = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
        except Exception as e:
            self.logger.debug(f"Port scan error for {ip}:{port}: {e}")
            return False
    
    async def _scan_host_ports(self, ip: str) -> List[int]:
        """Scan common ports on a host"""
        # Get all possible ports from device configurations
        all_ports = set()
        for device_config in self.config.SUPPORTED_DEVICES.values():
            all_ports.update(device_config.get('wifi_ports', []))
        
        # Add common service ports
        common_ports = [22, 23, 53, 80, 443, 515, 631, 8080, 8443, 9100]
        all_ports.update(common_ports)
        
        open_ports = []
        
        # Scan ports concurrently
        tasks = [self._scan_port(ip, port) for port in all_ports]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for port, result in zip(all_ports, results):
            if result is True:
                open_ports.append(port)
        
        return sorted(open_ports)
    
    async def _get_device_info_http(self, ip: str, port: int = 80) -> Dict[str, Any]:
        """Try to get device information via HTTP"""
        if not self.aiohttp_available:
            return {}
        
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Try common device info endpoints
                endpoints = [
                    f"http://{ip}:{port}/",
                    f"http://{ip}:{port}/info",
                    f"http://{ip}:{port}/status",
                    f"http://{ip}:{port}/device",
                    f"http://{ip}:{port}/api/info"
                ]
                
                for endpoint in endpoints:
                    try:
                        async with session.get(endpoint) as response:
                            if response.status == 200:
                                content_type = response.headers.get('content-type', '')
                                
                                if 'application/json' in content_type:
                                    data = await response.json()
                                    return {'source': endpoint, 'data': data}
                                else:
                                    text = await response.text()
                                    # Look for device information in HTML/text
                                    info = self._parse_device_info_from_text(text)
                                    if info:
                                        return {'source': endpoint, 'data': info}
                    except Exception:
                        continue
        
        except Exception as e:
            self.logger.debug(f"HTTP device info failed for {ip}: {e}")
        
        return {}
    
    def _parse_device_info_from_text(self, text: str) -> Dict[str, Any]:
        """Parse device information from HTML/text response"""
        info = {}
        text_lower = text.lower()
        
        # Look for common device identifiers
        if 'printer' in text_lower:
            info['device_type'] = 'printer'
        elif 'scanner' in text_lower:
            info['device_type'] = 'scanner'
        elif 'camera' in text_lower:
            info['device_type'] = 'camera'
        
        # Look for manufacturer information
        manufacturers = ['hp', 'canon', 'epson', 'brother', 'zebra', 'honeywell', 'symbol']
        for manufacturer in manufacturers:
            if manufacturer in text_lower:
                info['manufacturer'] = manufacturer.title()
                break
        
        return info
    
    async def _resolve_hostname(self, ip: str) -> Optional[str]:
        """Resolve hostname for IP address"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except (socket.herror, socket.gaierror):
            return None
    
    async def _get_mac_address(self, ip: str) -> Optional[str]:
        """Try to get MAC address for IP (works only on local network)"""
        try:
            # Try ARP table lookup
            if hasattr(asyncio, 'create_subprocess_exec'):
                process = await asyncio.create_subprocess_exec(
                    'arp', '-n', ip,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    output = stdout.decode()
                    # Parse ARP output for MAC address
                    lines = output.strip().split('\n')
                    for line in lines:
                        if ip in line and ':' in line:
                            parts = line.split()
                            for part in parts:
                                if ':' in part and len(part) == 17:  # MAC address format
                                    return part.upper()
        
        except Exception as e:
            self.logger.debug(f"MAC address lookup failed for {ip}: {e}")
        
        return None
    
    async def _scan_single_host(self, ip: str) -> Optional[NetworkDevice]:
        """Scan a single host for device information"""
        try:
            # First check if host is alive
            is_alive, response_time = await self._ping_host(ip)
            
            if not is_alive:
                return None
            
            self.logger.debug(f"Host {ip} is alive, scanning ports...")
            
            # Scan ports
            open_ports = await self._scan_host_ports(ip)
            
            if not open_ports:
                self.logger.debug(f"No open ports found on {ip}")
                return None
            
            # Get additional information
            hostname = await self._resolve_hostname(ip)
            mac_address = await self._get_mac_address(ip)
            
            # Try to get device info via HTTP
            device_info = {}
            if 80 in open_ports or 8080 in open_ports:
                port = 80 if 80 in open_ports else 8080
                device_info = await self._get_device_info_http(ip, port)
            
            # Identify device type
            device_type = self._identify_device_type(ip, open_ports, device_info)
            
            # Skip unknown devices if not configured to detect them
            if device_type == NetworkDeviceType.UNKNOWN:
                self.logger.debug(f"Unknown device type for {ip}, skipping")
                return None
            
            # Determine protocols
            protocols = []
            if 80 in open_ports or 8080 in open_ports:
                protocols.append(ConnectionProtocol.HTTP)
            if 443 in open_ports or 8443 in open_ports:
                protocols.append(ConnectionProtocol.HTTPS)
            if 9100 in open_ports:
                protocols.append(ConnectionProtocol.RAW)
            if 631 in open_ports:
                protocols.append(ConnectionProtocol.IPP)
            if 515 in open_ports:
                protocols.append(ConnectionProtocol.LPR)
            if 554 in open_ports:
                protocols.append(ConnectionProtocol.RTSP)
            
            # Extract manufacturer from device info
            manufacturer = None
            if device_info and 'data' in device_info:
                manufacturer = device_info['data'].get('manufacturer')
            
            device = NetworkDevice(
                ip_address=ip,
                hostname=hostname,
                mac_address=mac_address,
                device_type=device_type,
                open_ports=open_ports,
                protocols=protocols,
                manufacturer=manufacturer,
                device_info=device_info,
                response_time=response_time
            )
            
            return device
            
        except Exception as e:
            self.logger.error(f"Error scanning host {ip}: {e}")
            return None
    
    async def _handle_device_discovery(self, device: NetworkDevice):
        """Handle discovered network device"""
        try:
            ip = device.ip_address
            
            # Check if device is allowed (if MAC address is available)
            if device.mac_address and not self._is_device_allowed(device.mac_address):
                self.logger.debug(f"Device {ip} not in allowed list, skipping")
                return
            
            # Create or update device record
            if ip in self.discovered_devices:
                existing_device = self.discovered_devices[ip]
                existing_device.last_seen = time.time()
                existing_device.open_ports = device.open_ports
                existing_device.response_time = device.response_time
                if device.mac_address:
                    existing_device.mac_address = device.mac_address
                if device.hostname:
                    existing_device.hostname = device.hostname
            else:
                self.discovered_devices[ip] = device
                
                self.logger.info(f"Discovered network device: {device.hostname or ip} ({ip}) - Type: {device.device_type.value}")
                
                # Notify callback about new device
                if self.device_callback:
                    await self._safe_callback(device, 'discovered')
                
                # Auto-connect if enabled
                if self.config.AUTO_CONNECT_DEVICES and ip not in self.connection_tasks:
                    self.connection_tasks[ip] = asyncio.create_task(
                        self._connect_to_device(device)
                    )
        
        except Exception as e:
            self.logger.error(f"Error handling device discovery: {e}")
    
    def _is_device_allowed(self, mac_address: str) -> bool:
        """Check if device is allowed based on MAC address whitelist"""
        if not self.config.ALLOWED_DEVICE_MACS:
            return True  # Empty list means allow all
        return mac_address.upper() in [mac.upper() for mac in self.config.ALLOWED_DEVICE_MACS]
    
    async def _connect_to_device(self, device: NetworkDevice) -> bool:
        """Attempt to connect to a network device"""
        try:
            ip = device.ip_address
            self.logger.info(f"Attempting to connect to {device.hostname or ip} ({ip})")
            
            # Try different connection methods based on available protocols
            connected = False
            
            for protocol in device.protocols:
                if protocol == ConnectionProtocol.HTTP and self.aiohttp_available:
                    connected = await self._test_http_connection(device)
                elif protocol == ConnectionProtocol.RAW:
                    connected = await self._test_raw_connection(device)
                elif protocol == ConnectionProtocol.IPP:
                    connected = await self._test_ipp_connection(device)
                
                if connected:
                    break
            
            if connected:
                device.is_connected = True
                device.connection_attempts = 0
                self.connected_devices[ip] = device
                
                self.logger.info(f"Connected to {device.hostname or ip}")
                
                # Notify callback about connection
                if self.device_callback:
                    await self._safe_callback(device, 'connected')
                
                return True
            else:
                device.connection_attempts += 1
                
                # Check if we should stop trying to connect
                if device.connection_attempts >= self.config.MAX_RECONNECT_ATTEMPTS:
                    self.logger.warning(f"Max connection attempts reached for {device.hostname or ip}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to device {ip}: {e}")
            return False
        finally:
            # Clean up connection task
            if device.ip_address in self.connection_tasks:
                del self.connection_tasks[device.ip_address]
    
    async def _test_http_connection(self, device: NetworkDevice) -> bool:
        """Test HTTP connection to device"""
        if not self.aiohttp_available:
            return False
        
        try:
            port = 80 if 80 in device.open_ports else 8080
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"http://{device.ip_address}:{port}/") as response:
                    return response.status < 400
        
        except Exception:
            return False
    
    async def _test_raw_connection(self, device: NetworkDevice) -> bool:
        """Test raw TCP connection to device"""
        try:
            port = 9100  # Common raw printing port
            if port in device.open_ports:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(device.ip_address, port),
                    timeout=5
                )
                writer.close()
                await writer.wait_closed()
                return True
        except Exception:
            pass
        
        return False
    
    async def _test_ipp_connection(self, device: NetworkDevice) -> bool:
        """Test IPP connection to device"""
        try:
            port = 631
            if port in device.open_ports:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(device.ip_address, port),
                    timeout=5
                )
                writer.close()
                await writer.wait_closed()
                return True
        except Exception:
            pass
        
        return False
    
    async def _safe_callback(self, device: NetworkDevice, event: str):
        """Safely call the device callback"""
        try:
            if asyncio.iscoroutinefunction(self.device_callback):
                await self.device_callback(device, event)
            else:
                self.device_callback(device, event)
        except Exception as e:
            self.logger.error(f"Error in device callback: {e}")
    
    async def start_scanning(self):
        """Start network device scanning"""
        if not self.config.ENABLE_WIFI_DETECTION:
            self.logger.info("WiFi/Network detection disabled in config")
            return
        
        if self.is_scanning:
            self.logger.warning("Network scanning already active")
            return
        
        self.is_scanning = True
        self.logger.info(f"Starting network device scanning on {self.config.NETWORK_SCAN_RANGE}")
        
        try:
            while self.is_scanning:
                await self.scan_once()
                await asyncio.sleep(self.config.SCAN_INTERVAL)
        
        except Exception as e:
            self.logger.error(f"Error during network scanning: {e}")
        finally:
            self.is_scanning = False
    
    async def stop_scanning(self):
        """Stop network device scanning"""
        self.logger.info("Stopping network scanning")
        self.is_scanning = False
        
        # Cancel all connection tasks
        for task in self.connection_tasks.values():
            if not task.done():
                task.cancel()
        self.connection_tasks.clear()
        
        # Disconnect all devices
        for device in list(self.connected_devices.values()):
            await self._disconnect_device(device)
    
    async def scan_once(self) -> List[NetworkDevice]:
        """Perform a single network scan"""
        try:
            self.logger.info("Performing network scan")
            
            # Get all IP addresses in the network range
            ip_addresses = [str(ip) for ip in self.scan_network.hosts()]
            
            # Limit concurrent scans to avoid overwhelming the network
            semaphore = asyncio.Semaphore(50)
            
            async def scan_with_semaphore(ip):
                async with semaphore:
                    return await self._scan_single_host(ip)
            
            # Scan all hosts concurrently
            tasks = [scan_with_semaphore(ip) for ip in ip_addresses]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            discovered = []
            for result in results:
                if isinstance(result, NetworkDevice):
                    await self._handle_device_discovery(result)
                    discovered.append(result)
            
            self.logger.info(f"Network scan completed, found {len(discovered)} devices")
            return discovered
            
        except Exception as e:
            self.logger.error(f"Error during network scan: {e}")
            return []
    
    async def _disconnect_device(self, device: NetworkDevice):
        """Disconnect from a network device"""
        try:
            device.is_connected = False
            
            if device.ip_address in self.connected_devices:
                del self.connected_devices[device.ip_address]
            
            self.logger.info(f"Disconnected from {device.hostname or device.ip_address}")
            
            # Notify callback about disconnection
            if self.device_callback:
                await self._safe_callback(device, 'disconnected')
                
        except Exception as e:
            self.logger.error(f"Error disconnecting from {device.hostname or device.ip_address}: {e}")
    
    def get_discovered_devices(self) -> List[NetworkDevice]:
        """Get list of all discovered devices"""
        return list(self.discovered_devices.values())
    
    def get_connected_devices(self) -> List[NetworkDevice]:
        """Get list of connected devices"""
        return list(self.connected_devices.values())
    
    def get_device_by_ip(self, ip: str) -> Optional[NetworkDevice]:
        """Get device by IP address"""
        return self.discovered_devices.get(ip)        
    return False