{
    'name': 'Mystery Shopper Reimbursement',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Automaticallyy creates a vendor bill from an invoice to reimburse mystery shoppers.',
    'depends': ['account', 'product'],
    'data': [
        'views/product_template_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
