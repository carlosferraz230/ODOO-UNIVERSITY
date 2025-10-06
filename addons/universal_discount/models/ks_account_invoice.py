from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json


class KsGlobalDiscountInvoice(models.Model):
    # _inherit = "account.invoice"
    """ changing the model to account.move """
    _inherit = "account.move"

    ks_enable_discount = fields.Boolean(compute='ks_verify_discount')
    ks_sales_discount_account_id = fields.Integer(compute='ks_verify_discount')
    ks_purchase_discount_account_id = fields.Integer(compute='ks_verify_discount')
    ks_global_discount_type = fields.Selection([
        ('percent', 'Percentage'),
        ('amount', 'Amount')],
        string='Discount Type',
        readonly=True,
        states={'draft': [('readonly', False)],
                'sent': [('readonly', False)]},
        default='percent')
    ks_global_discount_rate = fields.Float('Discount',
                                           readonly=True,
                                           states={'draft': [('readonly', False)],
                                                   'sent': [('readonly', False)]})
    ks_amount_discount = fields.Monetary(string='Amount Discounted',
                                         readonly=True,
                                         compute='_compute_amount',
                                         store=True, track_visibility='always')

    def get_tax_line_details(self):
        """return: data for all taxes - @author: Hermenegildo Mulonga """
        tax_lines_data = []
        for line in self.invoice_line_ids:
            for tax_line in line.tax_ids:
                tax_lines_data.append({
                    'tax_exigibility': tax_line.tax_exigibility,
                    'tax_amount': (line.price_subtotal - line.ht_global_discount) * (tax_line.amount / 100),
                    'base_amount': line.price_subtotal - line.ht_global_discount,
                    'tax': tax_line,
                })
        return tax_lines_data

    @api.onchange('ks_global_discount_type')
    def onchange_discount_type(self):
        if self.ks_global_discount_type:
            self.ks_global_discount_rate = 0.0
            self.ks_amount_discount = 0.0
            self.onchange_discount_rate()

    @api.onchange('ks_global_discount_rate')
    def onchange_discount_rate(self):
        self.line_ids._onchange_price_subtotal()
        self._recompute_dynamic_lines(recompute_all_taxes=True)

    @api.depends('company_id.ks_enable_discount')
    def ks_verify_discount(self):
        for rec in self:
            rec.ks_enable_discount = rec.company_id.ks_enable_discount
            rec.ks_sales_discount_account_id = rec.company_id.ks_sales_discount_account.id
            rec.ks_purchase_discount_account_id = rec.company_id.ks_purchase_discount_account.id

    # 1. tax_line_ids is replaced with tax_line_id. 2. api.multi is also removed.
    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'ks_global_discount_type',
        'ks_global_discount_rate')
    def _compute_amount(self):
        super(KsGlobalDiscountInvoice, self)._compute_amount()
        for rec in self:
            for line in rec.invoice_line_ids:
                _price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                if line.price_subtotal != _price:
                    line.price_subtotal = line.price_subtotal + line.ht_global_discount  # subtotal without discount
            if not ('ks_global_tax_rate' in rec):
                rec.ks_calculate_discount()
            sign = rec.move_type in ['in_refund', 'out_refund'] and -1 or 1
            # rec.amount_total_company_signed = rec.amount_total * sign
            rec.amount_total_signed = rec.amount_total * sign

    # 
    def ks_calculate_discount(self):
        for rec in self:
            if rec.company_id.ht_discount_to == 'after_tax':  # @author: Hermenegildo Mulonga / Ticblac Solution - Serviços, Lda

                if rec.ks_global_discount_type == "amount":
                    if rec.ks_global_discount_rate > 0.0:
                        rec.ks_amount_discount = rec.ks_global_discount_rate if rec.amount_untaxed > 0 else 0

                elif rec.ks_global_discount_type == "percent":
                    if rec.ks_global_discount_rate > 0.0:
                        discount_amount = (rec.amount_untaxed + rec.amount_tax) * rec.ks_global_discount_rate / 100
                        rec.ks_amount_discount = discount_amount
                    else:
                        rec.ks_amount_discount = 0
                elif not rec.ks_global_discount_type:
                    rec.ks_global_discount_rate = 0
                    rec.ks_amount_discount = 0
                rec.amount_total = rec.amount_tax + rec.amount_untaxed - rec.ks_amount_discount
                rec._onchange_recompute_dynamic_lines()  # @author: Hermenegildo Mulonga / Ticblac Solution - Serviços, Lda
                rec.ks_update_universal_discount()
                rec._onchange_recompute_dynamic_lines()  # @author: Hermenegildo Mulonga / Ticblac Solution - Serviços, Lda
            else:
                rec._onchange_recompute_dynamic_lines()
                """@author: Hermenegildo Mulonga / Ticblac Solution - Serviços, Lda """
                if rec.ks_global_discount_type == "amount":
                    if rec.ks_global_discount_rate > 0:
                        rec.ks_amount_discount = rec.ks_global_discount_rate if rec.amount_untaxed > 0 else 0

                elif rec.ks_global_discount_type == "percent":
                    if rec.ks_global_discount_rate > 0:
                        price_subtotal = sum([
                            line.price_unit * (1 - (line.discount or 0.0) / 100.0) * line.quantity for line in
                            rec.invoice_line_ids
                        ])
                        rec.ks_amount_discount = price_subtotal * (rec.ks_global_discount_rate / 100)

                # rec.amount_total = rec.amount_untaxed + rec.amount_tax

    @api.constrains('ks_global_discount_rate')
    def ks_check_discount_value(self):
        if self.ks_global_discount_type == "percent":
            if self.ks_global_discount_rate > 100 or self.ks_global_discount_rate < 0:
                raise ValidationError('You cannot enter percentage value greater than 100.')
        else:
            if self.ks_global_discount_rate < 0 or self.amount_untaxed < 0:
                raise ValidationError(
                    'You cannot enter discount amount greater than actual cost or value lower than 0.')

    @api.model
    def _prepare_refund(self, invoice, invoice_date=None, date=None, description=None, journal_id=None):
        ks_res = super(KsGlobalDiscountInvoice, self)._prepare_refund(invoice, invoice_date=None, date=None,
                                                                      description=None, journal_id=None)
        ks_res['ks_global_discount_rate'] = self.ks_global_discount_rate
        ks_res['ks_global_discount_type'] = self.ks_global_discount_type
        return ks_res

    def ks_update_universal_discount(self):
        """This Function Updates the Universal Discount through Sale Order"""
        for rec in self:
            if rec.company_id.ht_discount_to == 'after_tax':
                already_exists = self.line_ids.filtered(
                    lambda line: line.name and line.name.find('Universal Discount') == 0)
                terms_lines = self.line_ids.filtered(
                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                other_lines = self.line_ids.filtered(
                    lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                if already_exists:
                    amount = rec.ks_amount_discount
                    if rec.ks_sales_discount_account_id \
                            and (rec.move_type == "out_invoice"
                                 or rec.move_type == "out_refund") \
                            and amount > 0:
                        if rec.move_type == "out_invoice":
                            already_exists.update({
                                'debit': amount > 0.0 and amount or 0.0,
                                'credit': amount < 0.0 and -amount or 0.0,
                            })
                        else:
                            already_exists.update({
                                'debit': amount < 0.0 and -amount or 0.0,
                                'credit': amount > 0.0 and amount or 0.0,
                            })
                    if rec.ks_purchase_discount_account_id \
                            and (rec.move_type == "in_invoice"
                                 or rec.move_type == "in_refund") \
                            and amount > 0:
                        if rec.move_type == "in_invoice":
                            already_exists.update({
                                'debit': amount < 0.0 and -amount or 0.0,
                                'credit': amount > 0.0 and amount or 0.0,
                            })
                        else:
                            already_exists.update({
                                'debit': amount > 0.0 and amount or 0.0,
                                'credit': amount < 0.0 and -amount or 0.0,
                            })
                    total_balance = sum(other_lines.mapped('balance'))
                    total_amount_currency = sum(other_lines.mapped('amount_currency'))
                    if not sum(terms_lines.mapped('debit')) == rec.amount_total_signed:
                        discount_percent = 0.0
                        total_discount = 0.0
                        for record in range(0, len(terms_lines)):
                            if len(self.invoice_payment_term_id.line_ids) >= len(terms_lines):
                                if self.invoice_payment_term_id.line_ids[record].value_amount:
                                    total_discount += self.invoice_payment_term_id.line_ids[record].value_amount
                                else:
                                    discount_percent = 100 - total_discount
                                terms_lines[record].update({
                                    'amount_currency': -total_amount_currency,
                                    'debit': (self.amount_total * (self.invoice_payment_term_id.line_ids[
                                                                       record].value_amount if not discount_percent else discount_percent) / 100) if total_balance < 0.0 else 0.0,
                                    'credit': ((self.amount_total * self.invoice_payment_term_id.line_ids[
                                        record].value_amount) / 100) if total_balance > 0.0 else 0.0
                                })
                            else:
                                terms_lines[record].update({
                                    'amount_currency': -total_amount_currency,
                                    'debit': self.amount_total if total_balance < 0.0 else 0.0,
                                    'credit': self.amount_total if total_balance > 0.0 else 0.0
                                })
                    else:
                        for record in terms_lines:
                            if rec.ks_global_discount_type == "percent":
                                record.update({
                                    'amount_currency': -total_amount_currency,
                                    'debit': (record.debit - ((
                                                                      record.debit * self.ks_global_discount_rate) / 100)) if total_balance < 0.0 else 0.0,
                                    'credit': (record.credit - ((
                                                                        record.credit * self.ks_global_discount_rate) / 100)) if total_balance > 0.0 else 0.0
                                })
                            else:
                                discount = rec.ks_global_discount_rate / len(terms_lines)
                                record.update({
                                    'amount_currency': -total_amount_currency,
                                    'debit': (record.debit - discount) if total_balance < 0.0 else 0.0,
                                    'credit': (record.credit - discount) if total_balance > 0.0 else 0.0
                                })
                if not already_exists and rec.ks_global_discount_rate > 0:
                    in_draft_mode = self != self._origin
                    if not in_draft_mode and rec.move_type == 'out_invoice':
                        rec._recompute_universal_discount_lines()
                    print()

    @api.onchange('ks_global_discount_rate', 'ks_global_discount_type', 'line_ids')
    def _recompute_universal_discount_lines(self):
        """This Function Create The General Entries for Universal Discount"""
        for rec in self:
            if rec.company_id.ht_discount_to == 'after_tax':
                type_list = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']
                if rec.ks_global_discount_rate > 0 and rec.move_type in type_list:
                    if rec.is_invoice(include_receipts=True):
                        in_draft_mode = self != self._origin
                        ks_name = "Universal Discount "
                        if rec.ks_global_discount_type == "amount":
                            ks_value = "of amount #" + str(self.ks_global_discount_rate)
                        elif rec.ks_global_discount_type == "percent":
                            ks_value = " @" + str(self.ks_global_discount_rate) + "%"
                        else:
                            ks_value = ''
                        ks_name = ks_name + ks_value
                        #           ("Invoice No: " + str(self.ids)
                        #            if self._origin.id
                        #            else (self.display_name))
                        terms_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        already_exists = self.line_ids.filtered(
                            lambda line: line.name and line.name.find('Universal Discount') == 0)
                        if already_exists:
                            amount = self.ks_amount_discount
                            if self.ks_sales_discount_account_id \
                                    and (self.move_type == "out_invoice"
                                         or self.move_type == "out_refund"):
                                if self.move_type == "out_invoice":
                                    already_exists.update({
                                        'name': ks_name,
                                        'debit': amount > 0.0 and amount or 0.0,
                                        'credit': amount < 0.0 and -amount or 0.0,
                                    })
                                else:
                                    already_exists.update({
                                        'name': ks_name,
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                    })
                            if self.ks_purchase_discount_account_id \
                                    and (self.move_type == "in_invoice"
                                         or self.move_type == "in_refund"):
                                if self.move_type == "in_invoice":
                                    already_exists.update({
                                        'name': ks_name,
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                    })
                                else:
                                    already_exists.update({
                                        'name': ks_name,
                                        'debit': amount > 0.0 and amount or 0.0,
                                        'credit': amount < 0.0 and -amount or 0.0,
                                    })
                        else:
                            new_tax_line = self.env['account.move.line']
                            create_method = in_draft_mode and \
                                            self.env['account.move.line'].new or \
                                            self.env['account.move.line'].create

                            if self.ks_sales_discount_account_id \
                                    and (self.move_type == "out_invoice"
                                         or self.move_type == "out_refund"):
                                amount = self.ks_amount_discount
                                dict = {
                                    'move_name': self.name,
                                    'name': ks_name,
                                    'price_unit': self.ks_amount_discount,
                                    'quantity': 1,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                    'account_id': self.ks_sales_discount_account_id,
                                    'move_id': self._origin,
                                    'date': self.date,
                                    'exclude_from_invoice_tab': True,
                                    'partner_id': terms_lines.partner_id.id,
                                    'company_id': terms_lines.company_id.id,
                                    'company_currency_id': terms_lines.company_currency_id.id,
                                }
                                if self.move_type == "out_invoice":
                                    dict.update({
                                        'debit': amount > 0.0 and amount or 0.0,
                                        'credit': amount < 0.0 and -amount or 0.0,
                                    })
                                else:
                                    dict.update({
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                    })
                                if in_draft_mode:
                                    self.line_ids += create_method(dict)
                                    # Updation of Invoice Line Id
                                    duplicate_id = self.invoice_line_ids.filtered(
                                        lambda line: line.name and line.name.find('Universal Discount') == 0)
                                    self.invoice_line_ids = self.invoice_line_ids - duplicate_id
                                else:
                                    dict.update({
                                        'price_unit': 0.0,
                                        'debit': 0.0,
                                        'credit': 0.0,
                                    })
                                    self.line_ids = [(0, 0, dict)]

                            if self.ks_purchase_discount_account_id \
                                    and (self.move_type == "in_invoice"
                                         or self.move_type == "in_refund"):
                                amount = self.ks_amount_discount
                                dict = {
                                    'move_name': self.name,
                                    'name': ks_name,
                                    'price_unit': self.ks_amount_discount,
                                    'quantity': 1,
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                    'account_id': self.ks_purchase_discount_account_id,
                                    'move_id': self.id,
                                    'date': self.date,
                                    'exclude_from_invoice_tab': True,
                                    'partner_id': terms_lines.partner_id.id,
                                    'company_id': terms_lines.company_id.id,
                                    'company_currency_id': terms_lines.company_currency_id.id,
                                }

                                if self.move_type == "in_invoice":
                                    dict.update({
                                        'debit': amount < 0.0 and -amount or 0.0,
                                        'credit': amount > 0.0 and amount or 0.0,
                                    })
                                else:
                                    dict.update({
                                        'debit': amount > 0.0 and amount or 0.0,
                                        'credit': amount < 0.0 and -amount or 0.0,
                                    })
                                self.line_ids += create_method(dict)
                                # updation of invoice line id
                                duplicate_id = self.invoice_line_ids.filtered(
                                    lambda line: line.name and line.name.find('Universal Discount') == 0)
                                self.invoice_line_ids = self.invoice_line_ids - duplicate_id

                        if in_draft_mode:
                            # Update the payement account amount
                            terms_lines = self.line_ids.filtered(
                                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                            other_lines = self.line_ids.filtered(
                                lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                            total_balance = sum(other_lines.mapped('balance'))
                            total_amount_currency = sum(other_lines.mapped('amount_currency'))
                            for record in terms_lines:
                                if rec.ks_global_discount_type == "percent":
                                    record.update({
                                        'amount_currency': -total_amount_currency,
                                        'debit': -(record.price_total - ((
                                                                                 record.price_total * rec.ks_global_discount_rate) / 100)) if total_balance < 0.0 else 0.0,
                                        'credit': record.price_total - ((
                                                                                record.price_total * rec.ks_global_discount_rate) / 100) if total_balance > 0.0 else 0.0
                                    })
                                elif rec.ks_global_discount_type == "amount":
                                    discount = rec.ks_global_discount_rate / len(terms_lines)
                                    record.update({
                                        'amount_currency': -total_amount_currency,
                                        'debit': -(record.price_total + discount) if total_balance < 0.0 else 0.0,
                                        'credit': record.price_total + discount if total_balance > 0.0 else 0.0
                                    })
                        else:
                            terms_lines = self.line_ids.filtered(
                                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                            other_lines = self.line_ids.filtered(
                                lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                            already_exists = self.line_ids.filtered(
                                lambda line: line.name and line.name.find('Universal Discount') == 0)
                            total_balance = sum(other_lines.mapped('balance')) + amount
                            total_amount_currency = sum(other_lines.mapped('amount_currency'))
                            line_ids = []
                            dict1 = {
                                'debit': amount > 0.0 and amount or 0.0,
                                'credit': amount < 0.0 and -amount or 0.0,
                            }
                            line_ids.append((1, already_exists.id, dict1))
                            dict2 = {
                                'debit': total_balance < 0.0 and -total_balance or 0.0,
                                'credit': total_balance > 0.0 and total_balance or 0.0,
                            }
                            # for records in already_exists:
                            #     records.update(dict1)
                            for record in terms_lines:
                                if rec.ks_global_discount_type == "percent":
                                    dict2 = {
                                        'amount_currency': -total_amount_currency,
                                        'debit': -(record.price_total - ((
                                                                                 record.price_total * rec.ks_global_discount_rate) / 100)) if total_balance < 0.0 else 0.0,
                                        'credit': record.price_total - ((
                                                                                record.price_total * rec.ks_global_discount_rate) / 100) if total_balance > 0.0 else 0.0
                                    }
                                elif rec.ks_global_discount_type == "amount":
                                    discount = rec.ks_global_discount_rate / len(terms_lines)
                                    dict2 = {
                                        'amount_currency': -total_amount_currency,
                                        'debit': -(
                                                record.price_total + discount) if total_balance < 0.0 else 0.0,
                                        'credit': record.price_total + discount if total_balance > 0.0 else 0.0
                                    }
                                line_ids.append((1, record.id, dict2))
                            # self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)]
                            self.line_ids = line_ids

                elif self.ks_global_discount_rate <= 0:
                    already_exists = self.line_ids.filtered(
                        lambda line: line.name and line.name.find('Universal Discount') == 0)
                    if already_exists:
                        self.line_ids -= already_exists
                        terms_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        other_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                        total_balance = sum(other_lines.mapped('balance'))
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        terms_lines.update({
                            'amount_currency': -total_amount_currency,
                            'debit': total_balance < 0.0 and -total_balance or 0.0,
                            'credit': total_balance > 0.0 and total_balance or 0.0,
                        })

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        """ Compute the dynamic tax lines of the journal entry.

        :param recompute_tax_base_amount: Flag forcing only the recomputation of the `tax_base_amount` field.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                _pu = base_line.price_unit
                _ht_amount_discount = 0.0  # global discount
                if base_line.move_id.company_id.ht_discount_to == 'before_tax':

                    if base_line.move_id.ks_global_discount_type == "percent":
                        if base_line.move_id.ks_global_discount_rate > 0:
                            _pu = base_line.price_unit * (
                                    1 - (base_line.move_id.ks_global_discount_rate or 0.0) / 100.0)
                            _ht_amount_discount = base_line.price_unit - _pu

                    elif base_line.move_id.ks_global_discount_type == "amount":
                        if base_line.move_id.ks_global_discount_rate > 0:
                            rate = (base_line.move_id.ks_global_discount_rate / base_line.price_unit) * 100
                            _pu = base_line.price_unit * (1 - (rate or 0.0) / 100.0)
                            _ht_amount_discount = base_line.price_unit - _pu

                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')
                price_unit_wo_discount = sign * _pu * (1 - (base_line.discount / 100.0))

            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.amount_currency

            return base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=move.always_tax_exigible,
            )

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        if not recompute_tax_base_amount:
            self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                if not recompute_tax_base_amount:
                    line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            if not recompute_tax_base_amount:
                line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(
                    tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'amount': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'],
                                                                                       tax_repartition_line,
                                                                                       tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict

        # ==== Pre-process taxes_map ====
        taxes_map = self._preprocess_taxes_map(taxes_map)

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                if not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

            # Don't create tax lines with zero balance.
            if currency.is_zero(taxes_map_entry['amount']):
                if taxes_map_entry['tax_line'] and not recompute_tax_base_amount:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue

            # tax_base_amount field is expressed using the company currency.
            tax_base_amount = currency._convert(taxes_map_entry['tax_base_amount'], self.company_currency_id,
                                                self.company_id, self.date or fields.Date.context_today(self))

            # Recompute only the tax_base_amount.
            if recompute_tax_base_amount:
                if taxes_map_entry['tax_line']:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            balance = currency._convert(
                taxes_map_entry['amount'],
                self.company_currency_id,
                self.company_id,
                self.date or fields.Date.context_today(self),
            )
            to_write_on_line = {
                'amount_currency': taxes_map_entry['amount'],
                'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'tax_base_amount': tax_base_amount,
            }

            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                # Create a new tax line.
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                    'account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                taxes_map_entry['tax_line'] = create_method({
                    **to_write_on_line,
                    'name': tax.name,
                    'move_id': self.id,
                    'partner_id': line.partner_id.id,
                    'company_id': line.company_id.id,
                    'company_currency_id': line.company_currency_id.id,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                taxes_map_entry['tax_line'].update(
                    taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))


class EsGlobalDiscountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    ht_global_discount = fields.Float(string="Global Discount")

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
                                            move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        _pu = price_unit * (1 - (discount / 100.0))
        _ht_amount_discount = 0.0  # global discount
        if self.move_id.company_id.ht_discount_to == 'before_tax':

            if self.move_id.ks_global_discount_type == "percent":
                if self.move_id.ks_global_discount_rate > 0:
                    _ht_amount_discount = _pu * (self.move_id.ks_global_discount_rate / 100.0)
                    _pu = _pu * (1 - (self.move_id.ks_global_discount_rate or 0.0) / 100.0)

            elif self.move_id.ks_global_discount_type == "amount":
                if self.move_id.ks_global_discount_rate > 0:
                    rate = (self.move_id.ks_global_discount_rate / _pu) * 100
                    _ht_amount_discount = _pu * (rate / 100.0)
                    _pu = _pu * (1 - (rate or 0.0) / 100.0)

        line_discount_price_unit = _pu
        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
                                                                                      quantity=quantity,
                                                                                      currency=currency,
                                                                                      product=product, partner=partner,
                                                                                      is_refund=move_type in (
                                                                                          'out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
            self.ht_global_discount = _ht_amount_discount
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
            self.ht_global_discount = _ht_amount_discount
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        _discount = 0.0
        current_price = {}
        for vals in vals_list:
            move = self.env['account.move'].browse(vals['move_id'])
            vals.setdefault('company_currency_id',
                            move.company_id.currency_id.id)  # important to bypass the ORM limitation where monetary fields are not rounded; more info in the commit message

            # Ensure balance == amount_currency in case of missing currency or same currency as the one from the
            # company.
            currency_id = vals.get('currency_id') or move.company_id.currency_id.id
            if currency_id == move.company_id.currency_id.id:
                balance = vals.get('debit', 0.0) - vals.get('credit', 0.0)
                vals.update({
                    'currency_id': currency_id,
                    'amount_currency': balance,
                })
            else:
                vals['amount_currency'] = vals.get('amount_currency', 0.0)

            if move.is_invoice(include_receipts=True):
                currency = move.currency_id
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                taxes = self.new({'tax_ids': vals.get('tax_ids', [])}).tax_ids
                tax_ids = set(taxes.ids)
                taxes = self.env['account.tax'].browse(tax_ids)

                # Ensure consistency between accounting & business fields.
                # As we can't express such synchronization as computed fields without cycling, we need to do it both
                # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
                # business [resp. accounting] fields are recomputed.
                if move.company_id.ht_discount_to == 'before_tax' and vals.get('product_id'):
                    if move.ks_global_discount_type == "amount":
                        if move.ks_global_discount_rate > 0:
                            _discount = (move.ks_global_discount_rate / vals.get('price_unit')) * 100
                            current_price[vals.get('product_id')] = vals.get('price_unit')
                    elif move.ks_global_discount_type == "percent":
                        if move.ks_global_discount_rate > 0:
                            _discount = move.ks_global_discount_rate
                            current_price[vals.get('product_id')] = vals.get('price_unit')

                if any(vals.get(field) for field in ACCOUNTING_FIELDS):
                    price_subtotal = self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                    ).get('price_subtotal', 0.0)
                    vals.update(self._get_fields_onchange_balance_model(
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        vals['amount_currency'],
                        move.move_type,
                        currency,
                        taxes,
                        price_subtotal
                    ))
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                    ))
                elif any(vals.get(field) for field in BUSINESS_FIELDS):
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                    ))
                    vals.update(self._get_fields_onchange_subtotal_model(
                        vals['price_subtotal'],
                        move.move_type,
                        currency,
                        move.company_id,
                        move.date,
                    ))

        lines = super(EsGlobalDiscountInvoiceLine, self).create(vals_list)
        for line in lines:
            if line.product_id and line.move_id.ks_global_discount_rate > 0:
                line.price_unit = current_price[line.product_id.id]

        moves = lines.mapped('move_id')
        if self._context.get('check_move_validity', True):
            moves._check_balanced()
        moves._check_fiscalyear_lock_date()
        lines._check_tax_lock_date()
        moves._synchronize_business_models({'line_ids'})

        return lines
