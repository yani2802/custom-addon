import usb.core
import usb.util
import platform

def detect_real_usb_devices():
    """Detect actual USB devices using pyusb"""
    devices = []
    
    # Find all USB devices
    usb_devices = usb.core.find(find_all=True)
    
    for device in usb_devices:
        try:
            # Get device information
            device_info = {
                'vendor_id': f'0x{device.idVendor:04x}',
                'product_id': f'0x{device.idProduct:04x}',
                'manufacturer': usb.util.get_string(device, device.iManufacturer),
                'product': usb.util.get_string(device, device.iProduct),
                'serial_number': usb.util.get_string(device, device.iSerialNumber),
            }
            
            # Identify device type based on vendor/product IDs
            device_type = identify_hardware_type(device_info)
            if device_type != 'unknown':
                devices.append({
                    'id': f"usb_{device_info['vendor_id']}_{device_info['product_id']}",
                    'name': f"{device_info['manufacturer']} {device_info['product']}",
                    'type': device_type,
                    'connection': 'USB',
                    'status': 'connected',
                    'device_info': device_info
                })
                
        except Exception as e:
            continue
    
    return devices

