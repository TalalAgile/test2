# -*- coding: utf-8 -*-
{
    'name': 'POS Dynamic Kit',
    'version': '1.0',
    'category': 'Point of Sale',
    'summary': 'Dynamic inventory deduction based on POS attributes',
    'description': """
        Allows products to be treated as dynamic kits where inventory deductions 
        are determined by the specific attribute values selected in POS.
    """,
    'depends': ['point_of_sale', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_attribute_value_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
