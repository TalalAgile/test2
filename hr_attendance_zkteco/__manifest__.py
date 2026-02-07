{
    'name': 'ZKTeco Attendance Integration',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Integrate ZKTeco attendance machines with Odoo Attendance',
    'description': """
        This module allows you to:
        - Configure ZKTeco attendance machine credentials (IP, Port).
        - Test connection to the machine.
        - Synchronize attendance logs automatically or manually.
    """,
    'author': 'Antigravity',
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'views/zk_machine_views.xml',
        'views/hr_employee_views.xml',
        'data/ir_cron.xml',
    ],



    'installable': True,

    'application': False,
    'license': 'LGPL-3',
}
