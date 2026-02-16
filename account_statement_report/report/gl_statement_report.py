# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.tools import format_date

import logging
_logger = logging.getLogger(__name__)

class GlStatementReport(models.AbstractModel):
    _name = 'report.account_statement_report.gl_statement_template'
    _description = 'GL Statement Report'

    def _get_account_move_entry(self, account_id, date_from, date_to, company_id, analytic_account_id=None, partner_id=None):
        """
        Fetch move lines for the report for a specific GL account.
        """
        domain = [
            ('account_id', '=', account_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', company_id)
        ]
        if analytic_account_id:
            domain.append(('analytic_distribution', 'ilike', f'"{analytic_account_id}"'))
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        return self.env['account.move.line'].search(domain, order='date, move_id')

    def _get_opening_balance(self, account_id, date_from, company_id, analytic_account_id=None, partner_id=None):
        """
        Calculate opening balance for a specific GL account before date_from.
        """
        domain = [
            ('account_id', '=', account_id),
            ('date', '<', date_from),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', company_id)
        ]
        if analytic_account_id:
            domain.append(('analytic_distribution', 'ilike', f'"{analytic_account_id}"'))
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
            
        # Use read_group for speed
        result = self.env['account.move.line'].read_group(
            domain, ['debit', 'credit'], []
        )
        opening_balance = 0.0
        if result:
            opening_balance = result[0]['debit'] - result[0]['credit']

        return opening_balance
    
    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info(f"Generating GL Report Values. Data: {data}")
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        account_id = data['form']['account_id']
        analytic_account_id = data['form'].get('analytic_account_id')
        partner_id = data['form'].get('partner_id')
        company_id = data['form']['company_id']
        # Use the language passed from the wizard
        lang = data['form'].get('language', 'en_US')
        self = self.with_context(lang=lang)
        
        company = self.env['res.company'].browse(company_id)
        account = self.env['account.account'].browse(account_id)
        analytic_account = self.env['account.analytic.account'].browse(analytic_account_id) if analytic_account_id else None
        partner = self.env['res.partner'].browse(partner_id) if partner_id else None
        
        # 1. Opening Balance
        opening_bal = self._get_opening_balance(account.id, date_from, company_id, analytic_account_id, partner_id)
        
        # 2. Lines
        move_lines = self._get_account_move_entry(account.id, date_from, date_to, company_id, analytic_account_id, partner_id)
        
        # 3. Process Lines
        docs = []
        current_balance = opening_bal
        total_debit = 0.0
        total_credit = 0.0
        
        def get_analytic_names(distribution):
            if not distribution:
                return ''
            try:
                # distribution is a dict like {"1": 100.0}
                account_ids = [int(k) for k in distribution.keys() if k.isdigit()]
                if not account_ids:
                    return ''
                accounts = self.env['account.analytic.account'].browse(account_ids)
                return ', '.join(accounts.mapped('name'))
            except Exception:
                return ''

        for line in move_lines:
            current_balance += line.balance
            
            # Totals
            total_debit += line.debit
            total_credit += line.credit

            docs.append({
                'date': str(line.date),
                'move_type': dict(line._fields['move_type']._description_selection(self.env)).get(line.move_id.move_type, line.move_id.move_type),
                'ref': line.move_id.name,
                'entry_ref': line.move_id.ref or '/',
                'name': line.name or '/', 
                'partner': line.partner_id.name or '',
                'analytic': get_analytic_names(line.analytic_distribution),
                'debit': line.debit,
                'credit': line.credit,
                'balance': current_balance,
            })
        
        # Dynamic Labels based on language
        if lang == 'ar_001':
            report_name = 'كشف حساب الأستاذ العام'
            labels = {
                'from': 'من تاريخ:',
                'to': 'الى تاريخ:',
                'opening_balance': 'الرصيد الافتتاحي:',
                'analytic': 'الحساب التحليلي:',
                'partner': 'الشريك:',
                'col_partner': 'الشريك',
                'col_analytic': 'الحساب التحليلي',
                'col_label': 'البيان',
                'col_ref': 'المرجع',
            }
        else:
            report_name = 'GL Statement of Account'
            labels = {
                'from': 'From:',
                'to': 'To:',
                'opening_balance': 'Opening Balance:',
                'analytic': 'Analytic Account:',
                'partner': 'Partner:',
                'col_partner': 'Partner',
                'col_analytic': 'Analytic Account',
                'col_label': 'Label',
                'col_ref': 'Reference',
            }

        return {
            'doc_ids': docids,
            'doc_model': 'gl.statement.wizard',
            'data': data,
            'docs': docs,
            'account': account,
            'analytic_account': analytic_account,
            'partner': partner,
            'date_from': date_from,
            'date_to': date_to,
            'opening_balance': opening_bal,
            'closing_balance': current_balance,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'company': company,
            'report_name': report_name,
            'labels': labels,
        }
