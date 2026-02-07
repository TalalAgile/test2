{
    'name': 'CRM Telegram AI Agent',
    'version': '1.1',
    'category': 'Sales/CRM',
    'summary': 'AI-powered Telegram bot for CRM Leads',
    'description': 'Automatically handles Telegram conversations using Gemini AI and syncs them with Odoo CRM Leads.',
    'depends': ['crm', 'mail', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
}
