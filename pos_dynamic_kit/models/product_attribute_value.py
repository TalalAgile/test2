# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    deduction_ids = fields.One2many(
        'pos.attribute.deduction', 
        'attribute_value_id', 
        string='Deduction Rules'
    )

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_dynamic_kit = fields.Boolean(
        string='Is Dynamic Kit', 
        help='If checked, this product will use dynamic attribute-based inventory deductions in POS.'
    )
