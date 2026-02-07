from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    zk_machine_id = fields.Char(string='ZK Machine ID', help="The ID assigned to this employee on the ZKTeco machine.")
