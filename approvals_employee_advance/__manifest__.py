{
    "name": "Employee Advance Approvals",
    "version": "1.0",
    "category": "Human Resources",
    "summary": "Manage employee advances through approval requests",
    "depends": ["approvals", "hr_payroll", "account"],
    "data": [
        "data/approval_category_data.xml",
        "views/approval_request_views.xml",
        "views/account_payment_views.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
