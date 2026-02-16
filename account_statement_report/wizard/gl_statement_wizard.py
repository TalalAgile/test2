# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64

class GlStatementWizard(models.TransientModel):
    _name = 'gl.statement.wizard'
    _description = 'GL Statement Wizard'

    account_id = fields.Many2one('account.account', string='Account', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    partner_id = fields.Many2one('res.partner', string='Partner')
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
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
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'account_id': self.account_id.id,
                'analytic_account_id': self.analytic_account_id.id,
                'partner_id': self.partner_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'language': self.language,
            },
        }
        report_template = self.env.ref('account_statement_report.action_report_gl_statement', raise_if_not_found=False)
        if not report_template:
            raise UserError(_("Report action not found."))
            
        action = report_template.report_action(self, data=data)
        if action.get('context'):
            action['context'].update({'lang': self.language})
        else:
            action['context'] = {'lang': self.language}
        return action

    def action_print_excel(self):
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("The 'xlsxwriter' module is not installed."))

        report_model = self.env['report.account_statement_report.gl_statement_template']
        data = {
            'form': {
                'account_id': self.account_id.id,
                'analytic_account_id': self.analytic_account_id.id,
                'partner_id': self.partner_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'language': self.language,
            }
        }
        
        # Switch language for Excel generation
        self = self.with_context(lang=self.language)
        
        report_data = report_model.with_context(lang=self.language)._get_report_values([self.id], data=data) 
        
        # Excel Logic
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('GL Statement')

        # Formats
        bold = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#f2f2f2'})
        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#e9ecef', 'text_wrap': True})
        num_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})
        border = workbook.add_format({'border': 1})
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})

        # Labels
        if self.language == 'ar_001':
            report_title = 'كشف حساب الأستاذ العام'
            lbl_from = 'من تاريخ'
            lbl_to = 'الى تاريخ'
            lbl_opening = 'الرصيد الافتتاحي'
            lbl_bal = 'الرصيد'
        else:
            report_title = 'GL Statement of Account'
            lbl_from = 'From:'
            lbl_to = 'To:'
            lbl_opening = 'Opening Balance:'
            lbl_bal = 'Balance'

        # Title/Header
        sheet.merge_range('A1:L1', report_title, title_format)
        
        sheet.write('A2', _('Account:'), bold)
        sheet.write('B2', report_data['account'].display_name, border)
        
        sheet.write('A3', lbl_from, bold)
        sheet.write('B3', str(self.date_from), border)
        sheet.write('C3', lbl_to, bold)
        sheet.write('D3', str(self.date_to), border)

        row_h = 3
        if self.analytic_account_id:
            lbl_analytic = 'Analytic Account:' if self.language != 'ar_001' else 'الحساب التحليلي:'
            sheet.write(row_h, 0, lbl_analytic, bold)
            sheet.write(row_h, 1, self.analytic_account_id.display_name, border)
            row_h += 1
        
        if self.partner_id:
            lbl_partner = 'Partner:' if self.language != 'ar_001' else 'الشريك:'
            sheet.write(row_h, 0, lbl_partner, bold)
            sheet.write(row_h, 1, self.partner_id.display_name, border)
            row_h += 1
        
        sheet.write(row_h, 0, lbl_opening, bold)
        sheet.write(row_h, 1, report_data['opening_balance'], num_format)

        # Tables Headers (Translated)
        headers = [
            _('Date'), _('Type'), _('Number'), 
            report_data['labels']['col_ref'],
            report_data['labels']['col_label'],
            report_data['labels']['col_partner'],
            report_data['labels']['col_analytic'],
            _('Debit'), _('Credit'), _('Balance')
        ]
        
        # Adjust for Arabic
        if self.language == 'ar_001':
            headers = [
                'التاريخ', 'النوع', 'الرقم', 
                report_data['labels']['col_ref'], 
                report_data['labels']['col_label'], 
                report_data['labels']['col_partner'], 
                report_data['labels']['col_analytic'], 
                'مدين', 'دائن', 'الرصيد'
            ]
            
        row = 6
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_format)
            sheet.set_column(col, col, 15)
        
        # Adjust Column widths
        sheet.set_column(3, 3, 20) # Ref
        sheet.set_column(4, 4, 30) # Label
        sheet.set_column(5, 5, 20) # Partner
        sheet.set_column(6, 6, 20) # Analytic
        
        row += 1
        
        # Rows
        for line in report_data['docs']:
            sheet.write(row, 0, line['date'], date_format)
            sheet.write(row, 1, line['move_type'], border)
            sheet.write(row, 2, line['ref'], border)
            sheet.write(row, 3, line['entry_ref'], border)
            sheet.write(row, 4, line['name'], border)
            sheet.write(row, 5, line['partner'], border)
            sheet.write(row, 6, line['analytic'], border)
            sheet.write(row, 7, line['debit'], num_format)
            sheet.write(row, 8, line['credit'], num_format)
            sheet.write(row, 9, line['balance'], num_format)
            row += 1

        # Balance Row
        lbl_total = _('Total Balance') if self.language != 'ar_001' else 'إجمالي الرصيد'
        sheet.write(row, 0, lbl_total, bold)
        sheet.write(row, 7, report_data.get('total_debit', 0.0), num_format)
        sheet.write(row, 8, report_data.get('total_credit', 0.0), num_format)
        sheet.write(row, 9, report_data['closing_balance'], num_format)
        row += 1

        workbook.close()
        output.seek(0)
        file_content = base64.b64encode(output.read())
        output.close()

        attachment_name = f'GL_Statement_{report_data["account"].code}_{self.date_to}.xlsx'
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
