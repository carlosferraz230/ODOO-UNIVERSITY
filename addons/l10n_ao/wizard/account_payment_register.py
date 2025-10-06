# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, frozendict


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    _description = "Payment Register Angola"

    amount_total_wth = fields.Monetary(string="Amount Total Withhold", currency_field='currency_id',
                                       compute="_compute_total_invoices_withhold_amount", store=True)
    amount_tax = fields.Monetary(string="Amount Tax", currency_field='currency_id',
                                 compute="_compute_amount_tax", store=True)
    amount_total_vat = fields.Monetary(string="Amount Total VAT", currency_field='currency_id',
                                       compute="_compute_total_invoices_vat_amount", store=True)
    deductible_wth = fields.Monetary(string="Withhold Apply", currency_field='currency_id',
                                     compute="_compute_amount_withhold", store=True)
    deductible_vat = fields.Monetary(string="Deductible IVA", currency_field='currency_id',
                                     compute="_compute_amount_deductible_vat", store=True)
    amount_total = fields.Monetary(string="Amount Total", currency_field='currency_id',
                                   compute="_compute_payment_amount_total", store=True)
    partner_deductible_vat = fields.Selection([
        ('none', 'Não deduz'),
        ('100', '100%'),
        ('50', '50%'),
    ], string="Partner Deductible Vat", default='none')

    @api.depends('line_ids')
    def _compute_amount_tax(self):
        """Compute tax amount"""
        for res in self:
            lines = res._get_invoices()
            _amount_tax = sum([line.amount_tax for line in lines])
            res.amount_tax = _amount_tax

    @api.depends('amount_total_wth', 'amount_total_vat')
    def _compute_payment_amount_total(self):
        for res in self:
            res.amount_total = 0.0
            if res.amount_total_wth > 0 and res.amount_total_vat > 0:
                _withhold_apply = sum([line._compute_amount_total_wth() for line in res._get_invoices()])
                amount_tax = sum([line.amount_tax for line in res._get_invoices()])
                _percent = res.percent_deductible_vat() / 100
                _amount_tax = amount_tax * _percent
                _amount_total = sum([line.amount_residual for line in res._get_invoices()])
                res.amount_total = _amount_total - _amount_tax - _withhold_apply
            elif res.amount_total_vat > 0:
                payment_diff = sum([line.payment_difference for line in res._get_invoices()])
                res.amount_total = payment_diff if payment_diff > 0.0 else res.amount_total_vat
            elif res.amount_total_wth > 0:
                # Total
                payment_diff = sum([line.payment_difference for line in res._get_invoices()])
                res.amount_total = payment_diff if payment_diff > 0.0 else res.amount_total_wth

    def _get_invoices(self):
        """Get invoice"""
        lines = self.line_ids.mapped('move_id')
        if not lines:
            return []
        return lines

    def _get_withholding_in_invoices(self):
        """return:  tax withholding(account.tax) - @author: Hermenegildo Mulonga"""
        tax_lines = self.env['account.tax']
        for move in self._get_invoices():
            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    if tax not in tax_lines and tax.tax_exigibility == 'withholding':
                        tax_lines += tax
        return tax_lines

    def _get_vat_in_invoices(self):
        """return:  tax vat(account.tax) - @author: Hermenegildo Mulonga"""
        tax_lines = self.env['account.tax']
        for move in self._get_invoices():
            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    if tax not in tax_lines and tax.tax_exigibility == 'on_invoice' and tax.amount > 0:
                        tax_lines += tax
        return tax_lines

    def check_partner_industry(self):
        for res in self:
            if res.partner_id.sector == '':
                res.partner_deductible_vat = '100'
            elif res.partner_id.industry_id and res.partner_id.industry_id.name in ['BANCO', 'BANK', 'IT', 'TI']:
                pass

    def percent_deductible_vat(self):
        for res in self:
            if res.partner_deductible_vat == 'none':
                return 0
            elif res.partner_deductible_vat == '100':
                return 100
            return 50

    @api.depends('line_ids', 'amount')
    def _compute_amount_withhold(self):

        for res in self:
            _withhold_apply = 0
            res._get_invoices()
            payment_rate = res.get_payment_rate()
            lines = res._get_invoices()
            _withhold_apply = sum([line._compute_amount_total_wth() for line in lines])
            res.deductible_wth = _withhold_apply * payment_rate['wth']

    @api.depends('line_ids', 'amount', 'partner_deductible_vat')
    def _compute_amount_deductible_vat(self):
        """Compute amount deductible vat"""
        for res in self:
            res.deductible_vat = _deductible_vat = 0
            lines = res._get_invoices()
            payment_rate = res.get_payment_rate()

            amount_tax = sum([line.amount_tax for line in lines])
            if amount_tax > 0 and res.partner_deductible_vat != 'none':
                _percent = res.percent_deductible_vat() / 100
                _amount_tax = amount_tax * _percent
                _deductible_vat = _amount_tax if _amount_tax < amount_tax else amount_tax
                self.deductible_vat = _deductible_vat * payment_rate['vat']
            res._compute_payment_difference()  # Re-calc difference

    @api.onchange('partner_deductible_vat')
    def line_deductible_vat(self):
        for res in self:
            if res.partner_deductible_vat:
                deductible_partner = list(set([line.partner_deductible_vat for line in res._get_invoices()]))
                part_inv = [line.name for line in res._get_invoices() if line.partner_deductible_vat != 'none']
                if len(deductible_partner) > 1:
                    raise UserError(_("%s invoices are partially paid with withholding tax,\n"
                                      "Invoice payments have to be handled individually") % part_inv)

                lines = self._get_invoices()
                for line in lines:
                    if line.partner_deductible_vat not in ['none'] and line.payment_state in ['partial']:
                        if line.partner_deductible_vat != res.partner_deductible_vat:
                            res.partner_deductible_vat = line.partner_deductible_vat
                    # line.partner_deductible_vat = self.partner_deductible_vat
                if res.partner_deductible_vat not in ['none']:
                    res.amount = res.amount_total
                else:
                    _amount_residual = sum([line.amount_residual for line in lines])
                    res.amount = _amount_residual

    @api.depends('line_ids')
    def _compute_total_invoices_withhold_amount(self):
        for res in self:
            wth_amount_total = sum([line.amount_total_wth for line in res._get_invoices()])
            res.amount_total_wth = wth_amount_total

    @api.depends('line_ids', 'partner_deductible_vat')
    def _compute_total_invoices_vat_amount(self):
        for res in self:
            res.amount_total_vat = 0.0
            if res.partner_deductible_vat != 'none':
                amount_total = sum([line.amount_total for line in res._get_invoices()])
                amount_tax = sum([line.amount_tax for line in res._get_invoices()])
                _amount_total = (
                        amount_total - (amount_tax * res.percent_deductible_vat() / 100)) if amount_tax > 0 else 0.0
                res.amount_total_vat = _amount_total  # Amount to current pay

    def get_payment_rate(self):
        inv_residual_total = sum([line.amount_residual for line in self._get_invoices()])

        # calculation of the payment of the withholding rate tax
        _withhold_apply = sum([line._compute_amount_total_wth() for line in self._get_invoices()])
        amount_tax = sum([line.amount_tax for line in self._get_invoices()])
        _percent = self.percent_deductible_vat() / 100
        _amount_tax = amount_tax * _percent
        amount_total_wth = sum([line.amount_total for line in self._get_invoices()]) - _amount_tax - _withhold_apply
        payment_rate_wth = (self.amount / amount_total_wth) if _withhold_apply > 0 else 0

        # calculation of the payment of the deductible VAT TAX
        amount_tax = sum([line.amount_tax for line in self._get_invoices()])
        _percent = self.percent_deductible_vat() / 100
        _amount_tax = amount_tax * _percent
        _amount_total = sum([line.amount_total for line in self._get_invoices()]) - _amount_tax - _withhold_apply
        payment_rate_vat = (self.amount / _amount_total) if amount_tax > 0 else 0.0

        if amount_total_wth == inv_residual_total:
            payment_rate_wth = 0
        if payment_rate_wth > 1:
            payment_rate_wth = 1
        if _amount_total == inv_residual_total:
            payment_rate_vat = 0
        if payment_rate_vat > 1:
            payment_rate_vat = 1
        return {
            'wth': payment_rate_wth,
            'vat': payment_rate_vat
        }

    def _set_invoice_difference(self):
        for res in self:
            invoices = res._get_invoices()

            for line in invoices:
                if line.move_type != 'entry':
                    if line.payment_difference == 0:
                        _percent = self.percent_deductible_vat() / 100
                        _amount_tax = line.amount_tax * _percent
                        if line.amount_total_wth == 0:
                            line.payment_difference = line.amount_total - _amount_tax
                        else:
                            line.payment_difference = line.amount_total_wth
                    line.payment_difference -= self.amount

    @api.depends('amount')
    def _compute_payment_difference(self):

        for wizard in self:
            _withhold_apply = self.deductible_wth
            _deductible_vat = self.deductible_vat
            if wizard.source_currency_id == wizard.currency_id:
                # Same currency.
                wizard.payment_difference = wizard.source_amount_currency - wizard.amount - _withhold_apply - _deductible_vat
            elif wizard.currency_id == wizard.company_id.currency_id:
                # Payment expressed on the company's currency.
                wizard.payment_difference = wizard.source_amount - wizard.amount - _withhold_apply - _deductible_vat
            else:
                # Foreign currency on payment different than the one set on the journal entries.
                amount_payment_currency = wizard.company_id.currency_id._convert(wizard.source_amount,
                                                                                 wizard.currency_id, wizard.company_id,
                                                                                 wizard.payment_date)
                wizard.payment_difference = amount_payment_currency - wizard.amount - _withhold_apply - _deductible_vat

    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)

        to_reconcile = []
        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard()
            payment_vals['deductible_wth'] = self.deductible_wth
            payment_vals['deductible_vat'] = self.deductible_vat
            payment_vals['partner_deductible_vat'] = self.partner_deductible_vat
            payment_vals_list = [payment_vals]

            to_reconcile.append(batches[0]['lines'])
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'lines': line,
                        })
                batches = new_batches

            payment_vals_list = []
            for batch_result in batches:
                payment_vals_list.append(self._create_payment_vals_from_batch(batch_result))
                to_reconcile.append(batch_result['lines'])

        payments = self.env['account.payment'].create(payment_vals_list)
        # If payments are made using a currency different than the source one, ensure the balance match exactly in
        # order to fully paid the source journal items.
        # For example, suppose a new currency B having a rate 100:1 regarding the company currency A.
        # If you try to pay 12.15A using 0.12B, the computed balance will be 12.00A for the payment instead of 12.15A.
        if edit_mode:
            for payment, lines in zip(payments, to_reconcile):
                # Batches are made using the same currency so making 'lines.currency_id' is ok.
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    source_balance = abs(sum(lines.mapped('amount_residual')))
                    payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
                    source_balance_converted = abs(source_balance) * payment_rate

                    # Translate the balance into the payment currency is order to be able to compare them.
                    # In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
                    # attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
                    # match.
                    payment_balance = abs(sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
                    if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
                        continue

                    delta_balance = source_balance - payment_balance

                    # Balance are already the same.
                    if self.company_currency_id.is_zero(delta_balance):
                        continue

                    # Fix the balance but make sure to peek the liquidity and counterpart lines first.
                    debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')

                    payment.move_id.write({'line_ids': [
                        (1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
                        (1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
                    ]})

        if self.deductible_wth > 0 and self.deductible_vat > 0:
            """counterpart VAT TAX + Withholding TAX - @author: Hermenegildo Mulonga"""

            domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
            for payment, lines in zip(payments, to_reconcile):
                payment_lines = payment.line_ids.filtered_domain(domain)
                withholding_tax_id = self._get_withholding_in_invoices()

                # Prepare the accounts to be used in offsetting the captive VAT.
                captive_vat_acc_id = self.env.ref("l10n_ao.1_account_chart_id320").id
                pay_captive_vat_acc_id = self.env.ref("l10n_ao.1_account_chart_id316").id
                captive_vat_account_id = self.env['account.account'].browse(captive_vat_acc_id)
                pay_captive_vat_account_id = self.env['account.account'].browse(pay_captive_vat_acc_id)

                _wth_vat = self.deductible_wth + self.deductible_vat

                pay_values = {
                    'credit': payment_lines.credit + _wth_vat
                } if payment_lines.account_internal_type == 'receivable' else {
                    'debit': payment_lines.debit + _wth_vat}

                values_tax_vat = {
                    'debit': self.deductible_vat if payment_lines.account_internal_type == 'receivable' else 0.0,
                    'credit': self.deductible_vat if payment_lines.account_internal_type == 'payable' else 0.0,
                    'account_id': captive_vat_account_id.id if payment_lines.account_internal_type == 'receivable' else pay_captive_vat_account_id.id,
                    # 'move_id': payment_lines.move_id.id,
                    'partner_id': payment.partner_id.id,
                    'journal_id': payment.journal_id.id,
                    'name': captive_vat_account_id.name if payment_lines.account_internal_type == 'receivable' else pay_captive_vat_account_id.name
                }
                values_tax_wth = {
                    'debit': self.deductible_wth if payment_lines.account_internal_type == 'receivable' else 0.0,
                    'credit': self.deductible_wth if payment_lines.account_internal_type == 'payable' else 0.0,
                    'account_id': withholding_tax_id.invoice_repartition_line_ids[1].account_id.id,
                    # 'move_id': payment_lines.move_id.id,
                    'partner_id': payment.partner_id.id,
                    'journal_id': payment.journal_id.id,
                    'name': withholding_tax_id.invoice_repartition_line_ids[1].account_id.name
                }
                payment_lines.move_id.write({'line_ids': [
                    (1, payment_lines.id, pay_values),
                    (0, 0, values_tax_vat),
                    (0, 0, values_tax_wth),
                ]})

        elif self.deductible_wth > 0:
            """counterpart of withholding - @author: Hermenegildo Mulonga"""

            domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
            for payment, lines in zip(payments, to_reconcile):
                payment_lines = payment.line_ids.filtered_domain(domain)
                withholding_tax_id = self._get_withholding_in_invoices()
                pay_values = {
                    'credit': payment_lines.credit + self.deductible_wth
                } if payment_lines.account_internal_type == 'receivable' else {
                    'debit': payment_lines.debit + self.deductible_wth}

                values_tax = {
                    'debit': self.deductible_wth if payment_lines.account_internal_type == 'receivable' else 0.0,
                    'credit': self.deductible_wth if payment_lines.account_internal_type == 'payable' else 0.0,
                    'account_id': withholding_tax_id.invoice_repartition_line_ids[1].account_id.id,
                    # 'move_id': payment_lines.move_id.id,
                    'partner_id': payment.partner_id.id,
                    'journal_id': payment.journal_id.id,
                    'name': withholding_tax_id.invoice_repartition_line_ids[1].account_id.name
                }

                payment_lines.move_id.write({'line_ids': [
                    (1, payment_lines.id, pay_values),
                    (0, 0, values_tax),
                ]})

        elif self.deductible_vat:
            """counterpart VAT TAX - @author: Hermenegildo Mulonga"""

            domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
            captive_vat_acc_id = self.env.ref("l10n_ao.1_account_chart_id320").id
            pay_captive_vat_acc_id = self.env.ref("l10n_ao.1_account_chart_id316").id
            captive_vat_account_id = self.env['account.account'].browse(captive_vat_acc_id)
            pay_captive_vat_account_id = self.env['account.account'].browse(pay_captive_vat_acc_id)

            for payment, lines in zip(payments, to_reconcile):
                payment_lines = payment.line_ids.filtered_domain(domain)
                values_tax = {
                    'debit': self.deductible_vat if payment_lines.account_internal_type == 'receivable' else 0.0,
                    'credit': self.deductible_vat if payment_lines.account_internal_type == 'payable' else 0.0,
                    'account_id': captive_vat_account_id.id if payment_lines.account_internal_type == 'receivable' else pay_captive_vat_account_id.id,
                    # 'move_id': payment_lines.move_id.id,
                    'partner_id': payment.partner_id.id,
                    'journal_id': payment.journal_id.id,
                    'name': captive_vat_account_id.name if payment_lines.account_internal_type == 'receivable' else pay_captive_vat_account_id.name
                }
                pay_values = {
                    'credit': payment_lines.credit + self.deductible_vat
                } if payment_lines.account_internal_type == 'receivable' else {
                    'debit': payment_lines.debit + self.deductible_vat}
                payment_lines.move_id.write({'line_ids': [
                    (1, payment_lines.id, pay_values),
                    (0, 0, values_tax),
                ]})

        payments.action_post()
        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
        for payment, lines in zip(payments, to_reconcile):
            # When using the payment tokens, the payment could not be posted at this point (e.g. the transaction failed)
            # and then, we can't perform the reconciliation.
            if payment.state != 'posted':
                continue

            payment_lines = payment.line_ids.filtered_domain(domain)
            for account in payment_lines.account_id:
                (payment_lines + lines) \
                    .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                    .reconcile()

        self._set_invoice_difference()
        self._check_register_payment()
        return payments

    def _check_register_payment(self):
        """Verify process of partner deductible"""
        lines = self._get_invoices()
        deductible_partner = list(set([line.partner_deductible_vat for line in self._get_invoices()]))
        part_inv = [line.name for line in self._get_invoices() if line.partner_deductible_vat != 'none']
        if len(deductible_partner) > 1:
            raise UserError(_("%s invoices are partially paid with withheld,\n"
                              "Invoice payments have to be handled individually") % part_inv)
        for line in lines:
            line.partner_deductible_vat = self.partner_deductible_vat
