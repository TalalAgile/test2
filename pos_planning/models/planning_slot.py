# -*- coding: utf-8 -*-
import pytz
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    booking_duration = fields.Float(string="Booking Duration (Minutes)", default=15.0)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pos_config_id = fields.Many2one(
        "pos.config",
        string="Point of Sale",
        help="The POS location where this booking was made.",
    )

    def action_cancel(self):
        """When cancelling a sales order, unlink all associated planning slots."""
        slots = (
            self.env["planning.slot"].sudo().search([("sale_order_id", "in", self.ids)])
        )
        if slots:
            slots.unlink()
        return super().action_cancel()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    planning_resource_id = fields.Many2one(
        "resource.resource",
        string="Assigned Professional",
        help="The employee/resource assigned to perform this service.",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        compute="_compute_employee_id",
        inverse="_inverse_employee_id",
        store=True,
        readonly=False,
    )

    @api.depends("planning_resource_id")
    def _compute_employee_id(self):
        for line in self:
            if line.planning_resource_id:
                employee = (
                    self.env["hr.employee"]
                    .sudo()
                    .search(
                        [("resource_id", "=", line.planning_resource_id.id)], limit=1
                    )
                )
                line.employee_id = employee.id if employee else False
            else:
                line.employee_id = False

    def _inverse_employee_id(self):
        for line in self:
            if line.employee_id:
                line.planning_resource_id = line.employee_id.resource_id
            else:
                line.planning_resource_id = False


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    pos_config_ids = fields.Many2many(
        "pos.config",
        string="Allowed POS",
        help="The Points of Sale this employee is allowed to work at.",
    )


class PlanningSlot(models.Model):
    _inherit = "planning.slot"

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        help="Customer linked to this booking.",
        index=True,
    )
    phone = fields.Char(related="partner_id.phone", string="Phone", readonly=True)
    sale_order_id = fields.Many2one(
        "sale.order", string="Linked Sales Order", readonly=True
    )
    # Hidden helper fields
    sale_line_id = fields.Many2one(
        "sale.order.line", string="Linked Sales Order Line", readonly=True
    )
    service_id = fields.Many2one("product.product", string="Primary Service")

    booking_line_ids = fields.Many2many(
        "product.product",
        string="Booked Services",
        help="Services linked to this shift.",
    )
    booking_status = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("ongoing", "Ongoing"),
            ("finished", "Finished"),
        ],
        string="Booking Status",
        default="not_started",
    )
    is_available_slot = fields.Boolean(
        string="Is Available Slot",
        default=False,
        help="If true, this is a shift available for booking, not an actual booking.",
    )
    pos_config_id = fields.Many2one(
        "pos.config",
        string="Location/POS",
        help="The Point of Sale this slot belongs to.",
    )

    @api.constrains("start_datetime", "end_datetime", "resource_id")
    def _check_resource_working_hours(self):
        for slot in self:
            if not slot.resource_id or not slot.start_datetime or not slot.end_datetime:
                continue
            calendar = slot.resource_id.calendar_id
            if not calendar:
                continue
            start_dt = slot.start_datetime.replace(tzinfo=pytz.UTC)
            end_dt = slot.end_datetime.replace(tzinfo=pytz.UTC)
            work_intervals = calendar._work_intervals_batch(
                start_dt, end_dt, resources=slot.resource_id
            )[slot.resource_id.id]
            total_work_seconds = sum(
                (i[1] - i[0]).total_seconds() for i in work_intervals
            )
            slot_seconds = (slot.end_datetime - slot.start_datetime).total_seconds()
            if total_work_seconds < slot_seconds:
                raise UserError(
                    _("The shift for %s is outside their working schedule.")
                    % slot.resource_id.name
                )

    @api.constrains("pos_config_id", "resource_id")
    def _check_pos_config_allowed(self):
        for slot in self:
            if slot.pos_config_id and slot.resource_id.employee_id:
                employee = slot.resource_id.employee_id
                if (
                    employee.pos_config_ids
                    and slot.pos_config_id not in employee.pos_config_ids
                ):
                    raise UserError(
                        _("Employee %s is not allowed to work in %s.")
                        % (employee.name, slot.pos_config_id.name)
                    )

    @api.depends("sale_order_id", "resource_id", "booking_status")
    def _compute_color(self):
        super()._compute_color()
        for slot in self:
            if not slot.resource_id:
                slot.color = 0
            elif slot.booking_status == "ongoing":
                slot.color = 4
            elif slot.booking_status == "finished":
                slot.color = 2
            elif slot.sale_order_id:
                slot.color = 3
            else:
                slot.color = 19

    @api.model_create_multi
    def create(self, vals_list):
        # logger muted for production
        for vals in vals_list:
            if not vals.get("pos_config_id") and vals.get("resource_id"):
                resource = self.env["resource.resource"].browse(vals["resource_id"])
                if resource.employee_id and resource.employee_id.pos_config_ids:
                    vals["pos_config_id"] = resource.employee_id.pos_config_ids[0].id
        
        records = super().create(vals_list)
        
        # Odoo's super().create might ignore our fields if they conflict with base logic
        # or if some template logic is running. We force them if they were provided in vals.
        for record, vals in zip(records, vals_list):
            force_vals = {}
            if vals.get('partner_id') and not record.partner_id:
                force_vals['partner_id'] = vals['partner_id']
            if vals.get('booking_line_ids') and not record.booking_line_ids:
                force_vals['booking_line_ids'] = vals['booking_line_ids']
            
            if force_vals:
                record.sudo().write(force_vals)
            
            # Now sync Sale Order - ensure record is loaded
            record._sync_sale_order()
            
        records._notify_planning_update("create")
        return records

    def write(self, vals):
        # logger muted
        if not vals.get("pos_config_id") and vals.get("resource_id"):
            resource = self.env["resource.resource"].browse(vals["resource_id"])
            if resource.employee_id and resource.employee_id.pos_config_ids:
                vals["pos_config_id"] = resource.employee_id.pos_config_ids[0].id
        res = super().write(vals)
        # Check if we need to sync SO or broadast update
        if any(f in vals for f in ["booking_line_ids", "partner_id", "resource_id", "is_available_slot", "start_datetime", "end_datetime"]):
            for record in self:
                record._sync_sale_order()
        self._notify_planning_update("write")
        return res

    def _sync_sale_order(self):
        """Creates or updates a linked Sale Order based on slot services and partner."""
        self.ensure_one()
        
        # Only create SO for actual bookings (not available shifts)
        if self.is_available_slot or not self.partner_id:
            return
            
        if not self.booking_line_ids:
            return

        so = self.sale_order_id
        if not so:
            so = self.env["sale.order"].sudo().create({
                "partner_id": self.partner_id.id,
                "pos_config_id": self.pos_config_id.id,
                "state": "draft",
            })
            self.sudo().write({"sale_order_id": so.id})
        else:
            if so.partner_id != self.partner_id:
                so.sudo().write({"partner_id": self.partner_id.id})
            if so.pos_config_id != self.pos_config_id:
                so.sudo().write({"pos_config_id": self.pos_config_id.id})

        # CRITICAL FIX: Aggregated sync
        # Find all slots sharing this SO to prevent "Record does not exist" conflicts
        all_slots_for_so = self.env["planning.slot"].sudo().search([("sale_order_id", "=", so.id)])
        all_requested_products = all_slots_for_so.mapped("booking_line_ids")
        
        # 1. Remove lines for products NOT in the global set of requested items for this SO
        stale_lines = so.order_line.filtered(lambda l: l.product_id not in all_requested_products)
        if stale_lines:
            stale_lines.sudo().unlink()
            
        # 2. Ensure every requested product has a line
        existing_products = so.order_line.mapped("product_id")
        for product in all_requested_products:
            if product not in existing_products:
                self.env["sale.order.line"].sudo().create({
                    "order_id": so.id,
                    "product_id": product.id,
                    "product_uom_qty": 1.0,
                    "planning_resource_id": self.resource_id.id, # Fallback to current resource
                })
            else:
                # Update employee/resource if needed (last one wins for the line)
                line = so.order_line.filtered(lambda l: l.product_id == product)
                # find which slot owns this specific product
                owner_slot = all_slots_for_so.filtered(lambda s: product in s.booking_line_ids)
                if owner_slot and line.planning_resource_id != owner_slot[0].resource_id:
                    line.sudo().write({"planning_resource_id": owner_slot[0].resource_id.id})
    def unlink(self):
        configs = self.mapped("pos_config_id")
        for slot in self:
            if slot.resource_id.employee_id:
                configs |= slot.resource_id.employee_id.pos_config_ids
        
        # Prepare data before unlink
        self._notify_planning_update("unlink")
        
        res = super().unlink()
        return res

    def _notify_planning_update(self, action_type="write"):
        return  # Notifications disabled by user request
        import uuid

        
        # Generate a unique message ID for client-side de-duplication
        msg_id = str(uuid.uuid4())

        payload = {
            "action": action_type,
            "slots": [],
            "id": msg_id, # De-duplication ID
        }
        
        if action_type != "unlink":
            for slot in self:
                payload["slots"].append({
                    "id": slot.id,
                    "start_datetime": fields.Datetime.to_string(slot.start_datetime),
                    "end_datetime": fields.Datetime.to_string(slot.end_datetime),
                    "resource_id": [slot.resource_id.id, slot.resource_id.name] if slot.resource_id else False,
                    "role_id": [slot.role_id.id, slot.role_id.name] if slot.role_id else False,
                    "name": slot.name,
                    "color": slot.color,
                    "is_available_slot": getattr(slot, 'is_available_slot', False),
                    "sale_order_id": [slot.sale_order_id.id, slot.sale_order_id.name] if slot.sale_order_id else False,
                    "booking_line_ids": slot.booking_line_ids.ids,
                    "booking_status": slot.booking_status,
                    "partner_id": [slot.partner_id.id, slot.partner_id.name] if slot.partner_id else False,
                    "phone": slot.phone,
                    "pos_config_id": slot.pos_config_id.id,
                })
        else:
            payload["slots"] = self.ids

        # Targeted notifications ONLY to the affected/active configs
        config_ids = self.mapped("pos_config_id").ids
        if not config_ids:
            # Fallback to active configs if no specific config is set
            configs = self.env["pos.config"].sudo().search([("active", "=", True)])
        else:
            configs = self.env["pos.config"].sudo().browse(config_ids)
            
        for config in configs:
            config._notify("PLANNING_UPDATE", payload)

    def action_open_planning_gantt_view(self):
        context = self.env.context.copy()
        domain = []
        if context.get("pos_config_id"):
            pos_id = int(context["pos_config_id"])
            domain = [
                ("pos_config_id", "=", pos_id),
                "|",
                ("resource_id.employee_id.pos_config_ids", "=", False),
                ("resource_id.employee_id.pos_config_ids", "in", [pos_id]),
            ]
            context["default_pos_config_id"] = pos_id
        return {
            "name": _("Planning"),
            "type": "ir.actions.act_window",
            "res_model": "planning.slot",
            "domain": domain,
            "views": [
                (self.env.ref("planning.planning_view_gantt").id, "gantt"),
                (self.env.ref("planning.planning_view_tree").id, "list"),
                (self.env.ref("planning.planning_view_form").id, "form"),
            ],
            "target": "current",
            "context": {
                "active_model": "planning.slot",
                "no_breadcrumbs": True,
                "hide_no_content_helper": True,
                **context,
            },
        }

    def action_save_and_add_another(self):
        """Saves current record and opens a new form with same customer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Shift'),
            'res_model': 'planning.slot',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_pos_config_id': self.pos_config_id.id,
                'default_resource_id': self.resource_id.id,
                'default_start_datetime': self.start_datetime,
                'default_end_datetime': self.end_datetime,
            }
        }

