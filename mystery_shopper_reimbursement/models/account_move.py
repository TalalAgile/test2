from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    reimbursement_bill_id = fields.Many2one(
        'account.move', 
        string='Reimbursement Bill', 
        readonly=True, 
        copy=False
    )

    def action_create_mystery_shopper_reimbursement(self):
        for move in self:
            if move.move_type != 'out_invoice':
                raise UserError(_("Reimbursement can only be created from a Customer Invoice."))
            
            if move.reimbursement_bill_id:
                raise UserError(_("A reimbursement bill already exists for this invoice."))

            reimbursable_lines = move.invoice_line_ids.filtered(lambda l: l.product_id.is_mystery_shopper_expense)
            if not reimbursable_lines:
                raise UserError(_("No mystery shopper expense products found on this invoice."))

            bill_vals = {
                'move_type': 'in_invoice',
                'partner_id': move.partner_id.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': move.name,
                'invoice_line_ids': [],
            }

            for line in reimbursable_lines:
                # Basic tax handling: use the same taxes as the invoice line
                bill_vals['invoice_line_ids'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'account_id': line.product_id.property_account_expense_id.id or line.product_id.categ_id.property_account_expense_categ_id.id,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                }))

            bill = self.env['account.move'].create(bill_vals)
            move.reimbursement_bill_id = bill.id
            
            return {
                'name': _('Vendor Bill'),
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': bill.id,
                'type': 'ir.actions.act_window',
            }
