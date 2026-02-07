# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import pytz
from odoo import _, fields, http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.http import request


class PosPlanningWeb(http.Controller):
    @http.route(["/planning/booking"], type="http", auth="public", website=True)
    def planning_booking(self, **kw):
        locations = request.env["pos.config"].sudo().search([("active", "=", True)])
        products = (
            request.env["product.product"]
            .sudo()
            .search([("available_in_pos", "=", True)])
        )
        resources = (
            request.env["resource.resource"]
            .sudo()
            .search([("employee_id.pos_config_ids", "!=", False)])
        )
        countries = request.env["res.country"].sudo().search([])
        return request.render(
            "pos_planning.booking_page",
            {
                "locations": locations,
                "products": products,
                "resources": resources,
                "countries": countries,
            },
        )

    @http.route(["/planning/booking/success"], type="http", auth="public", website=True)
    def booking_success(self, order_name=None, **kw):
        return request.render(
            "pos_planning.booking_success_page", {"order_name": order_name}
        )

    @http.route("/planning/get_work_intervals", type="jsonrpc", auth="user")
    def get_work_intervals(self, start_datetime, end_datetime, resource_ids=None):
        start = fields.Datetime.from_string(start_datetime)
        end = fields.Datetime.from_string(end_datetime)

        if not resource_ids:
            resources = request.env["resource.resource"].search(
                [("employee_id.pos_config_ids", "!=", False)]
            )
        else:
            resources = request.env["resource.resource"].browse(resource_ids)

        intervals = {}
        for resource in resources:
            calendar = resource.calendar_id
            if not calendar:
                continue

            work_intervals = calendar._work_intervals_batch(
                start, end, resources=resource
            )[resource.id]

            intervals[resource.id] = []
            for interval in work_intervals:
                intervals[resource.id].append(
                    {
                        "start": fields.Datetime.to_string(interval[0]),
                        "end": fields.Datetime.to_string(interval[1]),
                    }
                )

        return intervals

    @http.route(
        "/planning/get_available_slots", type="jsonrpc", auth="public", website=True
    )
    def get_available_slots(self, date, product_res_pairs=None, location_id=None, **kw):
        if not product_res_pairs:
            return []

        tz_name = (
            request.env.context.get("tz")
            or (request.website and request.website.company_id.partner_id.tz)
            or "UTC"
        )
        tz = pytz.timezone(tz_name)

        # Check if requested date is today
        requested_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.now(tz).date()
        if requested_date <= today:
            return []

        local_start = tz.localize(
            datetime.strptime(date + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        )
        local_end = tz.localize(
            datetime.strptime(date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        )
        utc_start_bound = local_start.astimezone(pytz.utc).replace(tzinfo=None)
        utc_end_bound = local_end.astimezone(pytz.utc).replace(tzinfo=None)

        services = []
        for pair in product_res_pairs:
            prod = request.env["product.product"].sudo().browse(int(pair["product_id"]))
            services.append(
                {
                    "prod_id": prod.id,
                    "name": prod.name,
                    "res_id": int(pair["res_id"]),
                    "duration": prod.booking_duration or 15,
                }
            )

        total_duration = sum(s["duration"] for s in services)
        resources = (
            request.env["resource.resource"]
            .sudo()
            .search([("employee_id.pos_config_ids", "!=", False)])
        )
        slots_domain = [
            ("start_datetime", "<=", utc_end_bound),
            ("end_datetime", ">=", utc_start_bound),
        ]
        all_slots = request.env["planning.slot"].sudo().search(slots_domain)

        start_aware = utc_start_bound.replace(tzinfo=pytz.UTC)
        end_aware = utc_end_bound.replace(tzinfo=pytz.UTC)
        resource_intervals = {}
        for r in resources:
            if r.calendar_id:
                resource_intervals[r.id] = r.calendar_id._work_intervals_batch(
                    start_aware, end_aware, resources=r
                )[r.id]
            else:
                resource_intervals[r.id] = []

        def get_resource_free_windows(res_id, start, end, loc_id):
            resource = resources.filtered(lambda r: r.id == res_id)
            if loc_id and resource.employee_id:
                emp = resource.employee_id
                if emp.pos_config_ids and int(loc_id) not in emp.pos_config_ids.ids:
                    return lambda s, e: False

            # Existing slots are considered busy windows
            busy = all_slots.filtered(lambda s: s.resource_id.id == res_id)

            def check_availability(s, e):
                if any(max(s, b.start_datetime) < min(e, b.end_datetime) for b in busy):
                    return False

                s_aware = s.replace(tzinfo=pytz.UTC)
                e_aware = e.replace(tzinfo=pytz.UTC)
                intervals = resource_intervals.get(res_id, [])
                for i_start, i_end, _ in intervals:
                    if i_start <= s_aware and i_end >= e_aware:
                        return True
                return False

            return check_availability

        intervals = []
        curr_utc = utc_start_bound
        while curr_utc + timedelta(minutes=total_duration) <= utc_end_bound:
            step_start = curr_utc
            valid_combo = True
            assignments = []
            for s in services:
                step_end = step_start + timedelta(minutes=s["duration"])
                found_res = None
                target_resources = (
                    resources.filtered(lambda r: r.id == s["res_id"])
                    if s["res_id"] > 0
                    else resources
                )
                for r in target_resources:
                    check_func = get_resource_free_windows(
                        r.id, utc_start_bound, utc_end_bound, location_id
                    )
                    if check_func(step_start, step_end):
                        found_res = r
                        break
                if found_res:
                    assignments.append(
                        {
                            "prod_id": s["prod_id"],
                            "prod_name": s["name"],
                            "res_id": found_res.id,
                            "res_name": found_res.name,
                            "start": step_start,
                            "end": step_end,
                        }
                    )
                    step_start = step_end
                else:
                    valid_combo = False
                    break

            if valid_combo:
                s_local = pytz.utc.localize(curr_utc).astimezone(tz)
                if s_local.strftime("%Y-%m-%d") == date:
                    intervals.append(
                        {
                            "start": s_local.strftime("%H:%M"),
                            "full_start": curr_utc.strftime("%Y-%m-%d %H:%M:%S"),
                            "duration": total_duration,
                            "assignments": [
                                {
                                    "prod_id": a["prod_id"],
                                    "res_id": a["res_id"],
                                    "res_name": a["res_name"],
                                }
                                for a in assignments
                            ],
                        }
                    )
            curr_utc += timedelta(minutes=15)
        return intervals

    @http.route(
        "/planning/confirm_booking", type="jsonrpc", auth="public", website=True
    )
    def confirm_booking(
        self,
        assignments,
        start_time,
        partner_name=None,
        phone=None,
        location_id=None,
        country_id=None,
        **kw,
    ):
        try:
            if not phone:
                return {"error": "Phone number is mandatory"}

            # Customer identification by Phone ONLY
            partner = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [("phone", "=", phone)],
                    limit=1,
                )
            )
            if not partner:
                vals = {"name": partner_name or phone, "phone": phone}
                if country_id:
                    vals["country_id"] = int(country_id)
                partner = (
                    request.env["res.partner"]
                    .sudo()
                    .create(vals)
                )

            sale_order = (
                request.env["sale.order"]
                .sudo()
                .create(
                    {
                        "partner_id": partner.id,
                    }
                )
            )

            curr_utc = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            for a in assignments:
                prod = request.env["product.product"].sudo().browse(int(a["prod_id"]))
                dur = prod.booking_duration or 15
                step_end = curr_utc + timedelta(minutes=dur)

                # Create Sales Order Line to ensure services and professional are filled
                sol = request.env["sale.order.line"].sudo().create({
                    "order_id": sale_order.id,
                    "product_id": prod.id,
                    "product_uom_qty": 1.0,
                    "planning_resource_id": int(a["res_id"]),
                })

                # Create the Planning Slot linked to the Sales Order and Line
                request.env["planning.slot"].sudo().create(
                    {
                        "start_datetime": curr_utc,
                        "end_datetime": step_end,
                        "resource_id": int(a["res_id"]),
                        "sale_order_id": sale_order.id,
                        "sale_line_id": sol.id,
                        "partner_id": partner.id,
                        "booking_line_ids": [(6, 0, [prod.id])],
                        "name": f"{partner.name} - {prod.name}",
                        "pos_config_id": int(location_id) if location_id else False,
                    }
                )
                curr_utc = step_end

            return {"success": True, "order_name": sale_order.name}
        except Exception as e:
            return {"error": str(e)}


class PosPlanningPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'booking_count' in counters:
            user = request.env.user
            if user.employee_id and user.employee_id.resource_id:
                values['booking_count'] = request.env['planning.slot'].sudo().search_count([
                    ('resource_id', '=', user.employee_id.resource_id.id)
                ])
            else:
                values['booking_count'] = 0
        return values

    @http.route(
        ["/my/bookings", "/my/bookings/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_bookings(
        self, page=1, date_begin=None, date_end=None, sortby=None, **kw
    ):
        user = request.env.user
        # Restrict to Employees Only (portal users who are employees)
        if not user.employee_id or not user.employee_id.resource_id:
            return request.render("http_routing.404")

        values = self._prepare_portal_layout_values()
        PlanningSlot = request.env["planning.slot"]

        # Only show slots assigned to the logged-in employee
        domain = [("resource_id", "=", user.employee_id.resource_id.id)]

        searchbar_sortings = {
            "date": {"label": _("Date"), "order": "start_datetime desc"},
            "name": {"label": _("Reference"), "order": "name"},
        }
        if not sortby:
            by_date = "start_datetime desc"
            sortby = "date"
        else:
            by_date = searchbar_sortings[sortby]["order"]

        count = PlanningSlot.sudo().search_count(domain)
        pager = portal_pager(
            url="/my/bookings",
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby},
            total=count,
            page=page,
            step=self._items_per_page,
        )

        slots = PlanningSlot.sudo().search(
            domain, order=by_date, limit=self._items_per_page, offset=pager["offset"]
        )

        values.update(
            {
                "slots": slots,
                "page_name": "booking",
                "pager": pager,
                "default_url": "/my/bookings",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
            }
        )
        return request.render("pos_planning.portal_my_bookings", values)

    @http.route(
        ["/my/bookings/<int:booking_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_booking(self, booking_id, **kw):
        user = request.env.user
        if not user.employee_id or not user.employee_id.resource_id:
            return request.render("http_routing.404")

        booking = request.env["planning.slot"].sudo().browse(booking_id)
        if not booking.exists() or booking.resource_id.id != user.employee_id.resource_id.id:
            return request.render("http_routing.404")

        values = self._prepare_portal_layout_values()
        values.update({
            "booking": booking,
            "page_name": "booking",
        })
        return request.render("pos_planning.portal_booking_page", values)