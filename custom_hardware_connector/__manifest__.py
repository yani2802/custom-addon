{
    'name': 'Custom Hardware Connector',
    'version': '1.0',
    'category': 'IoT',
    'summary': 'Connect hardware devices directly to Odoo without IoT Box',
    'description': """
        This module allows direct connection of hardware devices to Odoo:
        * Printers
        * Barcode scanners
        * POS peripherals
        * Scales
        * Other USB/Network devices
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/hardware_connector_security.xml',
        'security/ir.model.access.csv',
        'views/hardware_device_views.xml',
        'views/hardware_driver_views.xml',
        'views/hardware_device_type_views.xml',
        'views/hardware_connector_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_hardware_connector/static/src/components/**/*.js',
            'custom_hardware_connector/static/src/components/**/*.xml',
            'custom_hardware_connector/static/src/components/**/*.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}