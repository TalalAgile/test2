# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.tools import format_date

import logging
_logger = logging.getLogger(__name__)

class AccountStatementReport(models.AbstractModel):
    _name = 'report.account_statement_report.account_statement_template'
    _description = 'Account Statement Report'

    def _get_account_move_entry(self, accounts, partner_ids, date_from, date_to, company_id):
        """
        Fetch move lines for the report.
        """
        domain = [
            ('partner_id', 'in', partner_ids),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('account_id', 'in', accounts.ids),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', company_id)
        ]
        return self.env['account.move.line'].search(domain, order='date, move_id')

    def _get_opening_balance(self, accounts, partner_ids, date_from, company_id):
        """
        Calculate opening balance before date_from.
        """
        domain = [
            ('partner_id', 'in', partner_ids),
            ('date', '<', date_from),
            ('account_id', 'in', accounts.ids),
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', company_id)
        ]
        # Optimization: Use read_group for speed
        # 1. Main Balance (Company Currency)
        result_main = self.env['account.move.line'].read_group(
            domain, ['debit', 'credit'], []
        )
        opening_balance = 0.0
        if result_main:
            opening_balance = result_main[0]['debit'] - result_main[0]['credit']
            
        # 2. Currency Balances
        # We need to filter out lines where currency_id is the company currency or False (already handled in main logic usually, 
        # but account.move.line always has a currency_id? No, usually not if same as company, or it matches.)
        # Actually, best to just group by currency_id.
        
        result_currency = self.env['account.move.line'].read_group(
            domain + [('currency_id', '!=', False)], ['amount_currency'], ['currency_id']
        )
        
        opening_balance_currency = {}
        for res in result_currency:
            curr_id = res['currency_id'][0] if res['currency_id'] else False
            if curr_id and curr_id != company_id:
                opening_balance_currency[curr_id] = res['amount_currency']

        return opening_balance, opening_balance_currency

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info(f"Generating Account Report Values. Data: {data}")
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        partner_id = data['form']['partner_id']
        company_id = data['form']['company_id']
        account_type = data['form']['account_type']
        
        # Use the language passed from the wizard
        lang = data['form'].get('language', 'en_US')
        self = self.with_context(lang=lang)
        
        company = self.env['res.company'].browse(company_id)
        partner = self.env['res.partner'].browse(partner_id)
        
        # Determine accounts to query
        account_domain = []
        
        # Safer to use internal_type/account_type logic.
        types = []
        if account_type == 'receivable':
            types = ['receivable']
        elif account_type == 'payable':
            types = ['payable']
        else:
            types = ['receivable', 'payable']
            
        accepted_types = []
        if 'receivable' in types:
            accepted_types.append('asset_receivable')
        if 'payable' in types:
            accepted_types.append('liability_payable')
            
        accounts = self.env['account.account'].search(account_domain)
        accounts = accounts.filtered(lambda a: a.account_type in accepted_types)
        
        # 1. Opening Balance
        opening_bal, opening_bal_curr = self._get_opening_balance(accounts, [partner.id], date_from, company_id)
        
        # 2. Lines
        move_lines = self._get_account_move_entry(accounts, [partner.id], date_from, date_to, company_id)
        
        # 3. Process Lines
        docs = []
        current_balance = opening_bal
        total_debit = 0.0
        total_credit = 0.0
        
        for line in move_lines:
            current_balance += line.balance
            
            # Totals
            total_debit += line.debit
            total_credit += line.credit

            docs.append({
                'date': str(line.date),
                'move_type': dict(line._fields['move_type']._description_selection(self.env)).get(line.move_id.move_type, line.move_id.move_type), 
                'ref': line.move_id.name,
                'name': line.name or line.move_id.ref or '/', 
                'debit': line.debit,
                'credit': line.credit,
                'balance': current_balance,
            })
        
        # Dynamic Labels based on language
        if lang == 'ar_001':
            report_name = 'كشف حساب'
            labels = {
                'from': 'من تاريخ:',
                'to': 'الى تاريخ:',
                'opening_balance': 'الرصيد الافتتاحي:',
            }
        else:
            report_name = 'Statement of Account'
            labels = {
                'from': 'From:',
                'to': 'To:',
                'opening_balance': 'Opening Balance:',
            }

        return {
            'doc_ids': docids,
            'doc_model': 'account.statement.wizard',
            'data': data,
            'docs': docs,
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
