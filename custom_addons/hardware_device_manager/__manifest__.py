{
    'name': 'Hardware Device Manager',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'Manage Hardware Devices',
    'description': 'Simple hardware device management system',
    'depends': ['base'],
    'data': [
        'views/device_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
