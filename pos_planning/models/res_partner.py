# -*- coding: utf-8 -*-
from odoo import fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    secondary_phone = fields.Char(string="Secondary Phone")
