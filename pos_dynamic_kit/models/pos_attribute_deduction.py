# -*- coding: utf-8 -*-
from odoo import models, fields

class PosAttributeDeduction(models.Model):
    _name = 'pos.attribute.deduction'
    _description = 'POS Attribute Deduction Rule'

    attribute_value_id = fields.Many2one(
        'product.attribute.value', 
        string='Trigger Attribute Value', 
        required=True, 
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', 
        string='Ingredient to Deduct', 
        required=True
    )
    product_tmpl_ids = fields.Many2many(
        'product.template',
        string='Applicable Products',
        help='If set, this rule only applies to these specific products. If empty, it applies globally.'
    )
    deduction_line_ids = fields.One2many(
        'pos.attribute.deduction.line', 
        'deduction_id', 
        string='Contextual Rules'
    )

class PosAttributeDeductionLine(models.Model):
    _name = 'pos.attribute.deduction.line'
    _description = 'POS Attribute Deduction Context Line'

    deduction_id = fields.Many2one(
        'pos.attribute.deduction', 
        string='Parent Deduction', 
        ondelete='cascade'
    )
    condition_value_id = fields.Many2one(
        'product.attribute.value', 
        string='Condition (e.g. Size)',
        help='If selected, this deduction quantity will be used.'
    )
    quantity = fields.Float(
        string='Quantity', 
        default=1.0, 
        required=True
    )
