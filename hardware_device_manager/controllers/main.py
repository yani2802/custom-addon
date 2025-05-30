from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class HardwareDeviceController(http.Controller):
    
    @http.route('/hardware/devices', type='json', auth='user', methods=['GET'])
    def get_devices(self):
        """Get all hardware devices"""
        devices = request.env['hardware.device'].search([])
        return [{
            'id': device.id,
            'name': device.name,
            'device_type': device.device_type,
            'status': device.status,
        } for device in devices]
    
    @http.route('/hardware/device/scan', type='json', auth='user', methods=['POST'])
    def device_scan(self, device_id, scan_data, scan_type):
        """Record device scan data"""
        try:
            device = request.env['hardware.device'].browse(device_id)
            if device.exists():
                # Create scan log
                request.env['device.scan.log'].create({
                    'device_id': device_id,
                    'scan_data': scan_data,
                    'scan_type': scan_type,
                })
                
                # Update device last event
                device.write({
                    'last_event': fields.Datetime.now(),
                    'last_event_data': scan_data,
                })
                
                return {'success': True, 'message': 'Scan recorded successfully'}
            else:
                return {'success': False, 'error': 'Device not found'}
        except Exception as e:
            _logger.error("Error recording scan: %s", str(e))
            return {'success': False, 'error': str(e)}