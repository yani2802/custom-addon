from odoo import models, fields, api

class HardwareDevice(models.Model):
    _name = 'hardware.device'
    _description = 'Hardware Device'
    _rec_name = 'name'

    name = fields.Char('Device Name', required=True)
    device_type = fields.Selection([
        ('scanner', 'Barcode Scanner'),
        ('printer', 'Printer'),
        ('camera', 'Camera'),
    ], string='Device Type', required=True)
    
    status = fields.Selection([
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
    ], string='Status', default='disconnected')
    
    notes = fields.Text('Notes')
