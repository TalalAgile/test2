{
    'name': 'Sale WhatsApp Share',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Share Quotations and Sale Orders via WhatsApp',
    'description': """
This module adds a button to the Sale Order form that allows users to quickly share the quotation's portal URL via WhatsApp.
    """,
    'author': 'Agile Consulting',
    'depends': ['sale', 'portal'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
