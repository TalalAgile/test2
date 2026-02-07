from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    telegram_chat_id = fields.Char(string='Telegram Chat ID', copy=False)
    is_ai_agent_enabled = fields.Boolean(string='Enable AI Agent', default=True)
    ai_agent_context = fields.Text(string='AI Context', help="Instructions for the AI on how to handle this lead.")

    # CRM Lead inherited fields are already defined above.
