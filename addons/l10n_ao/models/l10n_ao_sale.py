from odoo import fields, models, api, _
import logging
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "Angola Sale"

    amount_total_wth = fields.Monetary('Total Retido', store=True, readonly=True)
    type = fields.Selection([
        ('PP', 'Pro-Forma'),
        ('OR', 'Orçamento'),
    ], string='Tipo', )

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if (vals.get('name', _('New')) == _('New')) and vals.get('type'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))

            if vals['type'] == 'PP':  # Pro-forma
                vals['name'] = self.env['ir.sequence'].next_by_code('pp.sale.order', sequence_date=seq_date) or _('New')
            elif vals['type'] == 'OR':  # Orçamento
                vals['name'] = self.env['ir.sequence'].next_by_code('or.sale.order', sequence_date=seq_date) or _(
                    'New')

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist.id)
        result = super(SaleOrder, self).create(vals)
        return result

    def _prepare_invoice(self):
        result = super(SaleOrder, self)._prepare_invoice()
        result['invoice_origin'] = self.name + ' - ' + fields.Datetime.to_string(self.date_order)[:10]
        # result['cost_center'] = self.cost_center.id
        return result

    @api.constrains('order_line', 'date_order')
    def check_field_lines(self):
        if len(self.order_line) == 0:
            raise UserError("Não exite nenhuma linha de ordem.\n"
                            "Adicionar Productos / Serviços nas linhas de ordem")
        for line in self.order_line:
            if line.price_unit < 0:
                raise UserError("O preço não pode ser negativo.")
            if line.discount < 0 or line.discount > 100:
                raise UserError("O desconto deve estar entre 0 - 100%.")

    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        # for picking in self.picking_ids:
        #     if self.cost_center:
        #         picking.cost_center = self.cost_center.id
        return result

    def get_tax_line_details(self):
        tax_lines_data = []
        for line in self.order_line:
            for tax_line in line.tax_id:
                tax_lines_data.append({
                    'tax_exigibility': tax_line.tax_exigibility,
                    'tax_amount': line.price_subtotal * (tax_line.amount / 100),
                    'base_amount': line.price_subtotal,
                    'tax': tax_line,
                })
        return tax_lines_data

    def tax_of_invoice(self):
        taxes = []
        for line in self.order_line:
            for tax in line.tax_id:
                taxes.append(tax)
        return list(set(taxes))

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    def print_quotation_ao(self):
        if self.type == 'PP':
            return self.env.ref('sale.action_report_pro_forma_invoice').report_action(self)
        elif self.type == 'OR':
            return self.env.ref('sale.action_report_saleorder').report_action(self)

    def get_exchange_rate(self, currency_name):
        currency_id = self.env['res.currency'].sudo().search([('name', '=', currency_name)])
        res = 100.00
        if currency_id:
            for rate in currency_id.rate_ids[-1]:
                if rate.company_rate:
                    res = rate.company_rate
            return res
        return res

    @staticmethod
    def _get_withhold_tax_line(price_subtotal, tax_id):
        """return: data for all taxes - @author: Hermenegildo Mulonga """
        tax_lines_data = []
        for tax in tax_id:
            if tax.tax_exigibility == 'withholding':
                return price_subtotal * (tax.amount / 100)
        return 0

    def get_withholding_tax(self):
        """return:  amount total tax withholding - @author: Hermenegildo Mulonga """
        withholding_tax_amount = 0
        for line in self.get_tax_line_details():
            if line['tax_exigibility'] == 'withholding':
                withholding_tax_amount += line['tax_amount']
        return withholding_tax_amount

    def ks_calculate_discount(self):
        for rec in self:
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

                _wth_tax_amount = rec.get_withholding_tax()
                rec.amount_tax = rec.amount_tax - _wth_tax_amount
                _amount_total = rec.amount_untaxed + rec.amount_tax
                rec.amount_total = _amount_total - rec.ks_amount_discount
                if _wth_tax_amount:
                    rec.amount_total_wth = (_amount_total - _wth_tax_amount) - rec.ks_amount_discount
            else:
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

                # rec.amount_tax = rec.amount_tax - rec.get_withholding_tax()
                _wth_tax_amount = rec.get_withholding_tax()
                _amount_total = rec.amount_untaxed + rec.amount_tax
                rec.amount_total = rec.amount_untaxed + rec.amount_tax
                if _wth_tax_amount:
                    rec.amount_total_wth = (rec.amount_total - _wth_tax_amount)