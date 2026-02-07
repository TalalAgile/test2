from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    telegram_bot_token = fields.Char(string='Telegram Bot Token', config_parameter='lead_telegram_agent.bot_token')
    openai_api_key = fields.Char(string='OpenAI API Key', config_parameter='lead_telegram_agent.openai_key')
    ai_system_prompt = fields.Char(string='Global AI System Prompt', config_parameter='lead_telegram_agent.system_prompt', 
                                  default="You are a helpful sales assistant for our company. Be polite, concise, and helpful.")
    ai_employee_role = fields.Selection([
        ('sales', 'Sales Agent'),
        ('accounting', 'Bookkeeper / Accountant'),
        ('inventory', 'Warehouse Manager'),
        ('general', 'Complete Virtual Employee')
    ], string='AI Job Position', config_parameter='lead_telegram_agent.ai_role', default='general')

    telegram_api_id = fields.Char(string='Telegram API ID', config_parameter='lead_telegram_agent.api_id')
    telegram_api_hash = fields.Char(string='Telegram API Hash', config_parameter='lead_telegram_agent.api_hash')
