# -*- coding: utf-8 -*-
{
    'name': 'Account Statement Report',
    'version': '1.0',
    'category': 'Accounting/Reporting',
    'summary': 'Detailed Statement of Account for Partners',
    'description': """
        This module adds a Statement of Account Report allowing users to:
        - View detailed transactions for Customers/Vendors.
        - Filter by Date Range and Account Type (Receivable/Payable).
        - See Opening Balance, Running Balance, and Multi-currency amounts.
        - Export to PDF and Excel.
    """,
    'author': 'Agile Consulting',
    'depends': ['account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_statement_wizard_view.xml',
        'wizard/gl_statement_wizard_view.xml',
        'report/account_statement_report_template.xml',
        'report/gl_statement_report_template.xml',
        'views/account_menu.xml',
        'views/sales_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
