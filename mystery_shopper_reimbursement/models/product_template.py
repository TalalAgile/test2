from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_mystery_shopper_expense = fields.Boolean(
        string='Mystery Shopper Expense',
        help='Check this if the product should be included in reimbursement vendor bills.'
    )
