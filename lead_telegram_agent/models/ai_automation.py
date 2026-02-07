from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import base64

class AiAutomation(models.AbstractModel):
    _name = 'ai.automation.mixin'
    _description = 'AI Automation Mixin'

    @api.model
    def action_ai_create_invoice_for_so(self, order_ref, chat_id=None, telegram_token=None):
        """Native Odoo method to convert a Sale Order into a posted Invoice.
        Accepts name (S00088) or ID.
        """
        # 1. Resolve Order
        SaleOrder = self.env['sale.order']
        order = False
        
        if isinstance(order_ref, int):
            order = SaleOrder.browse(order_ref)
        else:
            search_name = str(order_ref).strip()
            # Try exact, then variants
            order = SaleOrder.search(['|', ('name', '=ilike', search_name), ('name', '=ilike', search_name.replace('SO', 'S'))], limit=1)
            
            if not order:
                # Digit fallback
                import re
                digits = re.search(r'\d+$', search_name)
                if digits:
                    order = SaleOrder.search([('name', 'like', digits.group())], limit=1)

        if not order or not order.exists():
            return f"Error: Order '{order_ref}' not found."

        # 2. Process Workflow
        try:
            # Confirm if needed
            if order.state in ['draft', 'sent']:
                order.action_confirm()

            # Check for existing invoices
            if order.invoice_ids:
                invoice = order.invoice_ids[0]
            else:
                # Create Invoice
                invoice = order._create_invoices()
                if not invoice:
                    return f"Error: Could not create invoice for {order.name}. Check if lines are deliverable/invoicable."

            # Post Invoice
            if invoice.state == 'draft':
                invoice.action_post()

            # 3. Handle PDF Sending if Telegram info provided
            if chat_id and telegram_token:
                self._ai_send_telegram_pdf(invoice, chat_id, telegram_token)

            return f"Success: Invoice {invoice.name} created and posted for {order.name}."

        except Exception as e:
            return f"Error during native invoicing: {str(e)}"

    @api.model
    def action_ai_register_payment(self, invoice_ref, amount=None):
        """Native method to register payment for an invoice."""
        AccountMove = self.env['account.move']
        invoice = False
        
        if isinstance(invoice_ref, int):
            invoice = AccountMove.browse(invoice_ref)
        else:
            invoice = AccountMove.search([('name', '=ilike', str(invoice_ref).strip())], limit=1)

        if not invoice or not invoice.exists():
            return f"Error: Invoice '{invoice_ref}' not found."

        if invoice.payment_state in ['paid', 'in_payment']:
            return f"Invoice {invoice.name} is already paid."

        try:
            # Register payment
            payment_register_vals = {
                'payment_date': fields.Date.context_today(self),
                'amount': amount or invoice.amount_residual,
                'communication': invoice.name,
                'payment_method_line_id': self.env['account.payment.method.line'].search([('payment_type', '=', 'inbound')], limit=1).id,
                'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
            }
            
            # Use the wizard for standard Odoo behavior
            wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create(payment_register_vals)
            wizard.action_create_payments()
            
            return f"✅ Payment registered for {invoice.name}. Amount: {amount or invoice.amount_residual}."
        except Exception as e:
            return f"Error registering payment: {str(e)}"

    @api.model
    def action_ai_get_financial_summary(self):
        """Returns a quick summary of unpaid invoices and total receivables."""
        unpaid = self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', 'not in', ['paid', 'in_payment'])])
        total_residual = sum(unpaid.mapped('amount_residual'))
        
        summary = f"📊 **Financial Summary**\n"
        summary += f"- Total Receivables: {total_residual} {self.env.company.currency_id.symbol}\n"
        summary += f"- Unpaid Invoices: {len(unpaid)}\n\n"
        
        if unpaid:
            summary += "**Top Unpaid:**\n"
            for inv in unpaid[:5]:
                summary += f"• {inv.name} ({inv.partner_id.name}): {inv.amount_residual}\n"
        
        return summary

    @api.model
    def action_ai_search_suppliers(self, query):
        """Search for suppliers/vendors."""
        suppliers = self.env['res.partner'].search_read([('supplier_rank', '>', 0), ('name', 'ilike', query)], ['name', 'email', 'phone'], limit=5)
        if not suppliers:
            return "No suppliers found matching your query."
        return json.dumps(suppliers)

    @api.model
    def action_ai_create_purchase_order(self, supplier_id, products):
        """Draft a Purchase Order. 'products' should be a list of {'product_id': id, 'quantity': qty}."""
        try:
            supplier = self.env['res.partner'].browse(int(supplier_id))
            if not supplier.exists():
                return f"Error: Supplier ID {supplier_id} not found."

            po_vals = {
                'partner_id': supplier.id,
                'order_line': [],
            }

            for p in products:
                product = self.env['product.product'].browse(int(p['product_id']))
                if product.exists():
                    po_vals['order_line'].append((0, 0, {
                        'product_id': product.id,
                        'product_qty': p.get('quantity', 1),
                        'price_unit': product.standard_price or 0.0,
                        'name': product.name,
                    }))

            po = self.env['purchase.order'].create(po_vals)
            return f"✅ Purchase Order {po.name} drafted for {supplier.name}."
        except Exception as e:
            return f"Error drafting PO: {str(e)}"

    @api.model
    def _ai_send_telegram_pdf(self, invoice, chat_id, token):
        import requests
        report = self.env.ref('account.account_invoices')
        pdf_content, _ = report._render_qweb_pdf('account.report_invoice_with_payments', [invoice.id])
        
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        files = {'document': (f"{invoice.name}.pdf", pdf_content)}
        requests.post(url, data={'chat_id': chat_id, 'caption': f"Here is the invoice for {invoice.name}"}, files=files)

class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'ai.automation.mixin']

class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'ai.automation.mixin']
