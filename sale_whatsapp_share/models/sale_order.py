# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from urllib.parse import quote
import re

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_share_whatsapp_group(self):
        self.ensure_one()
        # Ensure the portal URL is generated
        self._portal_ensure_token()
        
        # Get the portal URL
        base_url = self.get_base_url()
        portal_url = f"{base_url}{self.get_portal_url()}"
        
        # Construct the message
        msg = _("Quotation: %s\nTotal: %s %s\nView Link: %s") % (
            self.name, self.amount_total, self.currency_id.symbol, portal_url
        )
        
        # URL encode the message
        encoded_msg = quote(msg)
        
        # Get and clean phone number defensively
        partner = self.partner_id
        # Some environments might lack 'mobile' or 'phone' fields on res.partner
        phone = getattr(partner, 'mobile', False) or getattr(partner, 'phone', False) or getattr(partner, 'secondary_phone', "") or ""
        
        # Remove non-numeric characters
        clean_phone = re.sub(r'\D', '', str(phone))
        
        # WhatsApp share link
        # If phone is available, it opens a direct chat. Otherwise, it opens contact selection.
        whatsapp_url = f"https://wa.me/{clean_phone}?text={encoded_msg}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': whatsapp_url,
            'target': 'new',
        }
