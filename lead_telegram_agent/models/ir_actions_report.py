from odoo import models, api
import base64

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """ Public wrapper for _render_qweb_pdf.
        Returns (base64_encoded_pdf, format) to avoid serialization errors in Odoo 19.
        """
        result, format = self._render_qweb_pdf(report_ref, res_ids, data=data)
        return base64.b64encode(result).decode('ascii'), format
