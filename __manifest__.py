{
    'name': 'Hardware Device Manager',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'Manage Barcode Scanners, NFC Readers, and QR Code Scanners',
    'description': """
        Hardware Device Manager
        ======================
        
        Complete hardware device management system for:
        * Barcode scanners
        * NFC readers  
        * QR code scanners
        * Network device discovery
        * Real-time monitoring
        * Scan history tracking
    """,
    
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/device_views.xml',
        'views/agent_views.xml',
        'views/scan_log_views.xml',
        'views/menu_views.xml',
        'views/payment_templates.xml',
        'data/device_data.xml',
        'wizards/device_discovery_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hardware_device_manager/static/src/js/**/*',
            'hardware_device_manager/static/src/css/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
