# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64

import logging
_logger = logging.getLogger(__name__)

class AccountStatementWizard(models.TransientModel):
    _name = 'account.statement.wizard'
    _description = 'Account Statement Wizard'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    account_type = fields.Selection([
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('all', 'All')
    ], string='Account Type', default='all', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    language = fields.Selection([
        ('en_US', 'English'),
        ('ar_001', 'Arabic'),
    ], string='Language', default='en_US', required=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_("Start Date must be before End Date."))

    def action_print_pdf(self):
        self.ensure_one()
        _logger.info(f"Account Statement PDF Request: Partner={self.partner_id.name}, Lang={self.language}, Type={self.account_type}")
        
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'partner_id': self.partner_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'account_type': self.account_type,
                'company_id': self.company_id.id,
                'report_name': self.env.context.get('report_name'),
                'language': self.language,
            },
        }
        _logger.info(f"Report Data Prepared: {data}")
        
        report_template = self.env.ref('account_statement_report.action_report_account_statement', raise_if_not_found=False)
        if report_template and not report_template.exists():
            report_template = False
            
        if not report_template:
            report_template = self.env['ir.actions.report'].search([('report_name', '=', 'account_statement_report.account_statement_template')], limit=1)

        if not report_template:
            raise UserError(_("Report action not found."))
            
        # Call with selected language context
        action = report_template.with_context(lang=self.language).report_action(self, data=data)
        
        # Ensure the returned action context and data also have the selected language
        if action.get('context'):
            action['context'].update({'lang': self.language})
        else:
            action['context'] = {'lang': self.language}
            
        if 'data' in action and 'form' in action['data']:
            action['data']['form']['language'] = self.language
            
        _logger.info(f"Report Action Returned: {action}")
        return action

    def action_print_excel(self):
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("The 'xlsxwriter' module is not installed."))

        report_model = self.env['report.account_statement_report.account_statement_template']
        data = {
            'form': {
                'partner_id': self.partner_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'account_type': self.account_type,
                'company_id': self.company_id.id,
                'report_name': self.env.context.get('report_name'),
                'language': self.language,
            }
        }
        
        # Switch language for Excel generation
        self = self.with_context(lang=self.language)
        
        report_data = report_model.with_context(lang=self.language)._get_report_values([self.id], data=data) 
        
        # Excel Logic
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Statement')

        # Formats
        bold = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#f2f2f2'})
        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#e9ecef', 'text_wrap': True})
        num_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})
        border = workbook.add_format({'border': 1})
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})

        # Title/Header
        if self.language == 'ar_001':
            report_title = 'كشف حساب'
            lbl_from = 'من تاريخ'
            lbl_to = 'الى تاريخ'
            lbl_opening = 'الرصيد الافتتاحي'
        else:
            report_title = 'Statement of Account'
            lbl_from = 'From:'
            lbl_to = 'To:'
            lbl_opening = 'Opening Balance:'
            
        sheet.merge_range('A1:L1', report_title, title_format)
        sheet.write('A2', _('Partner:'), bold)
        sheet.write('B2', report_data['partner'].name, border)
        sheet.write('A3', lbl_from, bold)
        sheet.write('B3', str(self.date_from), border)
        sheet.write('C3', lbl_to, bold)
        sheet.write('D3', str(self.date_to), border)
        
        sheet.write('A4', lbl_opening, bold)
        sheet.write('B4', report_data['opening_balance'], num_format)

        # Table Headers
        headers = [
            _('Date'), _('Type'), _('Number'), _('Description'), 
            _('Debit'), _('Credit'), _('Balance')
        ]
        row = 6
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_format)
            sheet.set_column(col, col, 15)
        
        # Adjust Description width
        sheet.set_column(3, 3, 40)
        
        row += 1
        
        # Rows
        for line in report_data['docs']:
            sheet.write(row, 0, line['date'], date_format)
            sheet.write(row, 1, line['move_type'], border)
            sheet.write(row, 2, line['ref'], border)
            sheet.write(row, 3, line['name'], border)
            sheet.write(row, 4, line['debit'], num_format)
            sheet.write(row, 5, line['credit'], num_format)
            sheet.write(row, 6, line['balance'], num_format)
            row += 1

        # Balance Row (Totals + Closing Balance)
        sheet.write(row, 0, _('Balance'), bold)
        sheet.write(row, 4, report_data.get('total_debit', 0.0), num_format)
        sheet.write(row, 5, report_data.get('total_credit', 0.0), num_format)
        sheet.write(row, 6, report_data['closing_balance'], num_format)
        row += 1

        workbook.close()
        output.seek(0)
        file_content = base64.b64encode(output.read())
        output.close()

        attachment_name = f'Statement_{report_data["partner"].name}_{self.date_to}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': file_content,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
