from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class CustomerPortalAdvance(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'advance_count' in counters:
            employee = request.env.user.employee_id
            if employee:
                category = request.env.ref('approvals_employee_advance.approval_category_employee_advance', raise_if_not_found=False)
                if category:
                    advance_count = request.env['approval.request'].search_count([
                        ('employee_id', '=', employee.id),
                        ('category_id', '=', category.id)
                    ])
                    values['advance_count'] = advance_count
                else:
                    values['advance_count'] = 0
            else:
                values['advance_count'] = 0
        return values

    @http.route(['/my/advances', '/my/advances/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_advances(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        employee = request.env.user.employee_id
        if not employee:
            return request.render("portal.portal_layout", values)

        ApprovalRequest = request.env['approval.request']
        category = request.env.ref('approvals_employee_advance.approval_category_employee_advance', raise_if_not_found=False)
        if not category:
             return request.render("portal.portal_layout", values)

        domain = [('employee_id', '=', employee.id), ('category_id', '=', category.id)]

        # count for pager
        advance_count = ApprovalRequest.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/advances",
            total=advance_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        advances = ApprovalRequest.search(domain, limit=self._items_per_page, offset=pager['offset'], order='create_date desc')

        values.update({
            'advances': advances,
            'page_name': 'advance',
            'pager': pager,
            'default_url': '/my/advances',
        })
        return request.render("approvals_employee_advance.portal_my_advances", values)

    @http.route(['/my/advances/<int:advance_id>'], type='http', auth="user", website=True)
    def portal_my_advance_detail(self, advance_id, **kw):
        advance = request.env['approval.request'].browse(advance_id)
        if not advance.exists() or advance.employee_id != request.env.user.employee_id:
            return request.redirect('/my/advances')
        
        values = {
            'advance': advance,
            'page_name': 'advance',
        }
        return request.render("approvals_employee_advance.portal_advance_page", values)

    @http.route(['/my/advances/new'], type='http', auth="user", website=True)
    def portal_new_advance(self, **kw):
        employee = request.env.user.employee_id
        if not employee:
            return request.redirect('/my')

        if request.httprequest.method == 'POST':
            category = request.env.ref('approvals_employee_advance.approval_category_employee_advance')
            vals = {
                'name': _('Advance Request - %s') % employee.name,
                'category_id': category.id,
                'request_owner_id': request.env.user.id,
                'employee_id': employee.id,
                'amount': float(kw.get('amount', 0)),
                'reason': kw.get('reason'),
            }
            new_request = request.env['approval.request'].create(vals)
            # Submit the request automatically
            new_request.action_confirm()
            return request.redirect('/my/advances')

        return request.render("approvals_employee_advance.portal_create_advance", {})
