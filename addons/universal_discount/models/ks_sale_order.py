# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import json

try:
    from dicttoxml import dicttoxml
except ImportError as imp:
    pass


class KsGlobalDiscountSales(models.Model):
    _inherit = "sale.order"

    ks_global_discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')],
                                               string='Discount Type',
                                               readonly=True,
                                               states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                               default='percent')
    ks_global_discount_rate = fields.Float('Discount',
                                           readonly=True,
                                           states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    ks_amount_discount = fields.Monetary(string='Amount Discounted', readonly=True, compute='_amount_all', store=True,
                                         track_visibility='always')
    ks_enable_discount = fields.Boolean(compute='ks_verify_discount')

    def get_tax_line_details(self):
        """return: data for all taxes - @author: Hermenegildo Mulonga """
        tax_lines_data = []
        for line in self.order_line:
            for tax_line in line.tax_id:
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

    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        def compute_taxes(order_line):
            """calc global discount before tax, @author: Hermenegildo Mulonga / Ticblac Solution - Serviços, Lda """
            _pu = order_line.price_unit  # price unit
            if order_line.order_id.company_id.ht_discount_to == 'before_tax':

                """ change the method of calculating discount_type rate or amount is equals 0.0 
                 @author: Wilson Paiva / Ticblac Solution - Serviços, Lda 
                """
                if order_line.order_id.ks_global_discount_type == "percent":
                    if order_line.order_id.ks_global_discount_rate == 0:
                        self.ks_amount_discount = 0.0
                    if order_line.order_id.ks_global_discount_rate > 0:
                        _pu = order_line.price_unit * (1 - (order_line.order_id.ks_global_discount_rate or 0.0) / 100.0)

                elif order_line.order_id.ks_global_discount_type == "amount":
                    if order_line.order_id.ks_global_discount_rate == 0:
                        self.ks_amount_discount = 0.0
                    if order_line.order_id.ks_global_discount_rate > 0:
                        rate = (order_line.order_id.ks_global_discount_rate / order_line.price_unit) * 100
                        _pu = order_line.price_unit * (1 - (rate or 0.0) / 100.0)

            price = _pu * (1 - (order_line.discount or 0.0) / 100.0)
            order = order_line.order_id
            return order_line.tax_id._origin.compute_all(price, order.currency_id, order_line.product_uom_qty,
                                                         product=order_line.product_id,
                                                         partner=order.partner_shipping_id)

        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order.order_line,
                                                                                         compute_taxes)
            tax_totals = account_move._get_tax_totals(order.partner_id, tax_lines_data, order.amount_total,
                                                      order.amount_untaxed, order.currency_id)
            order.tax_totals_json = json.dumps(tax_totals)

    @api.depends('company_id.ks_enable_discount')
    def ks_verify_discount(self):
        for rec in self:
            rec.ks_enable_discount = rec.company_id.ks_enable_discount

    @api.depends('order_line.price_total', 'ks_global_discount_rate', 'ks_global_discount_type')
    def _amount_all(self):
        # res = super(KsGlobalDiscountSales, self)._amount_all()
        """
            Compute the total amounts of the SO.
            @author: Hermenegildo Mulonga
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax - self._get_withhold_tax_line(line.price_subtotal, line.tax_id)
                line.price_subtotal = line.price_subtotal + line.ht_global_discount  # subtotal without discount
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })
        for rec in self:
            if not ('ks_global_tax_rate' in rec):
                rec.ks_calculate_discount()
        # return res

    def _prepare_invoice(self):
        res = super(KsGlobalDiscountSales, self)._prepare_invoice()
        res['ks_global_discount_rate'] = self.ks_global_discount_rate
        res['ks_global_discount_type'] = self.ks_global_discount_type
        return res

    # 
    def ks_calculate_discount(self):
        for rec in self:
            """ change the method of calculating discount  @author: Hermenegildo Mulonga / Ticblac Solution - Serviços, Lda """
            if rec.company_id.ht_discount_to == 'after_tax':
                if rec.ks_global_discount_type == "amount":
                    if rec.ks_global_discount_rate > 0.0:
                        rec.ks_amount_discount = rec.ks_global_discount_rate if rec.amount_untaxed > 0 else 0

                elif rec.ks_global_discount_type == "percent":
                    if rec.ks_global_discount_rate != 0.0:
                        discount_amount = (rec.amount_untaxed + rec.amount_tax) * rec.ks_global_discount_rate / 100
                        rec.ks_amount_discount = discount_amount
                    else:
                        rec.ks_amount_discount = 0
                elif not rec.ks_global_discount_type:
                    rec.ks_amount_discount = 0
                    rec.ks_global_discount_rate = 0
                rec.amount_total = rec.amount_untaxed + rec.amount_tax - rec.ks_amount_discount

                _wth_tax_amount = rec.get_withholding_tax()
                rec.amount_tax = rec.amount_tax - _wth_tax_amount
                _amount_total = rec.amount_untaxed + rec.amount_tax
                rec.amount_total = _amount_total - rec.ks_amount_discount
                if _wth_tax_amount:
                    rec.amount_total_wth = (_amount_total - _wth_tax_amount) - rec.ks_amount_discount
            else:
                """@author: Hermenegildo Mulonga / Ticblac Solution - Serviços, Lda """
                if rec.ks_global_discount_type == "amount":
                    if rec.ks_global_discount_rate > 0:
                        rec.ks_amount_discount = rec.ks_global_discount_rate if rec.amount_untaxed > 0 else 0

                elif rec.ks_global_discount_type == "percent":
                    if rec.ks_global_discount_rate > 0:
                        price_subtotal = sum([
                            line.price_unit * (1 - (line.discount or 0.0) / 100.0) * line.product_uom_qty for line in
                            rec.order_line
                        ])
                        rec.ks_amount_discount = price_subtotal * (rec.ks_global_discount_rate / 100)
                # rec.amount_total = rec.amount_untaxed + rec.amount_tax

                _wth_tax_amount = rec.get_withholding_tax()
                _amount_total = rec.amount_untaxed + rec.amount_tax
                rec.amount_total = rec.amount_untaxed + rec.amount_tax
                if _wth_tax_amount:
                    rec.amount_total_wth = (rec.amount_total - _wth_tax_amount)


    @api.constrains('ks_global_discount_rate')
    def ks_check_discount_value(self):
        if self.ks_global_discount_type == "percent":
            if self.ks_global_discount_rate > 100 or self.ks_global_discount_rate < 0:
                raise ValidationError('You cannot enter percentage value greater than 100.')
        else:
            if self.ks_global_discount_rate < 0 or self.ks_global_discount_rate > self.amount_untaxed:
                raise ValidationError(
                    'You cannot enter discount amount greater than actual cost or value lower than 0.')


class ESSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    ht_global_discount = fields.Float(string="Global Discount")

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'order_id.ks_global_discount_rate')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            """calc global discount before tax, @author: Hermenegildo Mulonga / Ticblac Solution - Serviços, Lda """
            _pu = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            _ht_amount_discount = 0.0  # global discount
            if line.order_id.company_id.ht_discount_to == 'before_tax':

                if line.order_id.ks_global_discount_type == "percent":
                    if line.order_id.ks_global_discount_rate > 0:
                        _ht_amount_discount = _pu * (line.order_id.ks_global_discount_rate / 100)
                        _pu = _pu * (1 - (line.order_id.ks_global_discount_rate or 0.0) / 100.0)

                elif line.order_id.ks_global_discount_type == "amount":
                    if line.order_id.ks_global_discount_rate > 0:
                        rate = (line.order_id.ks_global_discount_rate / _pu) * 100
                        _ht_amount_discount = _pu * (rate / 100.0)
                        _pu = _pu * (1 - (rate or 0.0) / 100.0)

            price = _pu  # price unit
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],  # PRICE + TAX
                'price_subtotal': taxes['total_excluded'],
                'ht_global_discount': _ht_amount_discount,
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])


class KsSaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoice(self, order, so_line, amount):
        invoice = super(KsSaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        if invoice:
            invoice['ks_global_discount_rate'] = order.ks_global_discount_rate
            invoice['ks_global_discount_type'] = order.ks_global_discount_type
        return invoice
