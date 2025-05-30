from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class HardwareDevice(models.Model):
    _name = 'hardware.device'
    _description = 'Hardware Device'
    _order = 'name'

    name = fields.Char('Device Name', required=True)
    device_id = fields.Char('Device ID', required=True)
    device_type = fields.Selection([
        ('barcode_scanner', 'Barcode Scanner'),
        ('nfc_reader', 'NFC Reader'),
        ('qr_scanner', 'QR Scanner'),
        ('printer', 'Printer'),
        ('payment', 'Payment Terminal'),
        ('camera', 'Camera'),
    ], string='Device Type', required=True)
    
    status = fields.Selection([
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
    ], string='Status', default='disconnected')
    
    agent_id = fields.Many2one('hardware.agent', string='Agent')
    last_event = fields.Datetime('Last Event')
    last_event_data = fields.Text('Last Event Data')
    
    # Configuration fields
    printer_config = fields.Text('Printer Configuration')
    payment_terminal_config = fields.Text('Payment Terminal Configuration')
    
    def action_print_test(self):
        """Test print functionality"""
        _logger.info(f"Test print requested for device {self.name}")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Test print sent to {self.name}',
                'type': 'success',
            }
        }
    
    def action_process_payment(self):
        """Test payment processing"""
        _logger.info(f"Test payment requested for device {self.name}")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Test payment initiated on {self.name}',
                'type': 'success',
            }
        }