from odoo import models, fields, api

class DeviceScanLog(models.Model):
    _name = 'device.scan.log'
    _description = 'Device Scan Log'
    _order = 'create_date desc'

    device_id = fields.Many2one('hardware.device', string='Device', required=True)
    scan_data = fields.Text('Scan Data')
    scan_type = fields.Selection([
        ('barcode', 'Barcode'),
        ('qr', 'QR Code'),
        ('nfc', 'NFC'),
    ], string='Scan Type')
    
    processed = fields.Boolean('Processed', default=False)
    error_message = fields.Text('Error Message')
