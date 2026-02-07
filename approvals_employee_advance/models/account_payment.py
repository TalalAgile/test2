from odoo import _, api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    approval_request_id = fields.Many2one(
        "approval.request", string="Approval Request", copy=False
    )
    salary_attachment_id = fields.Many2one(
        "hr.salary.attachment", string="Salary Adjustment", copy=False
    )

    def action_post(self):
        """
        Overridden to create a Salary Adjustment (hr.salary.attachment)
        when an employee advance payment is posted.
        """
        res = super().action_post()

        salary_attachment_model = self.env["hr.salary.attachment"]

        for payment in self:
            if (
                payment.approval_request_id
                and payment.approval_request_id.is_employee_advance
            ):
                employee = payment.approval_request_id.employee_id
                if not employee:
                    continue

                # Check if a salary adjustment already exists for this payment/request
                existing_adjustment = salary_attachment_model.search(
                    [
                        ("employee_ids", "in", employee.id),
                        ("description", "ilike", payment.approval_request_id.name),
                        ("total_amount", "=", payment.amount),
                    ],
                    limit=1,
                )
                if existing_adjustment:
                    continue

                # Attempt to find a standard input type for salary attachments
                input_type = self.env.ref(
                    "hr_payroll.input_attachment_salary", raise_if_not_found=False
                )
                if not input_type:
                    input_type = self.env["hr.payslip.input.type"].search(
                        [("available_in_attachments", "=", True)], limit=1
                    )

                # Create the salary adjustment record
                # This will automatically deduct the amount from the employee's next payslip
                adjustment = salary_attachment_model.create(
                    {
                        "employee_ids": [(4, employee.id)],
                        "description": _("Advance: %s")
                        % (payment.memo or payment.approval_request_id.name),
                        "other_input_type_id": input_type.id if input_type else False,
                        "monthly_amount": payment.amount,
                        "total_amount": payment.amount,
                        "duration_type": "one",
                        "is_refund": True,
                        "date_start": fields.Date.context_today(payment),
                    }
                )
                payment.salary_attachment_id = adjustment

        return res
