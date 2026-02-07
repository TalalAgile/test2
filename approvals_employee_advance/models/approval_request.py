from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    request_owner_id = fields.Many2one(readonly=True)
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    payment_id = fields.Many2one("account.payment", string="Payment", copy=False)
    payment_count = fields.Integer(compute="_compute_payment_count")
    is_employee_advance = fields.Boolean(compute="_compute_is_employee_advance")

    @api.depends("category_id")
    def _compute_is_employee_advance(self):
        advance_category = self.env.ref(
            "approvals_employee_advance.approval_category_employee_advance",
            raise_if_not_found=False,
        )
        for request in self:
            request.is_employee_advance = (
                advance_category and request.category_id == advance_category
            )

    def _compute_payment_count(self):
        for request in self:
            request.payment_count = 1 if request.payment_id else 0

    def action_create_payment(self):
        self.ensure_one()
        if self.payment_id:
            return self.action_open_payment()

        if not self.employee_id:
            raise UserError(_("An employee must be set to create an advance payment."))

        payment_vals = {
            "date": fields.Date.context_today(self),
            "amount": self.amount,
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": (
                getattr(self.employee_id, "address_id", self.env["res.partner"]).id
                or getattr(
                    self.employee_id, "work_contact_id", self.env["res.partner"]
                ).id
                or getattr(
                    self.employee_id.user_id, "partner_id", self.env["res.partner"]
                ).id
                or self.request_owner_id.partner_id.id
            ),
            "memo": self.name,
            "approval_request_id": self.id,
        }

        payment = self.env["account.payment"].create(payment_vals)
        self.payment_id = payment

        return self.action_open_payment()

    def action_open_payment(self):
        self.ensure_one()
        return {
            "name": _("Payment"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": self.payment_id.id,
            "view_mode": "form",
            "target": "current",
        }
