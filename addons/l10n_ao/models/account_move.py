from odoo import fields, models, api, _
from odoo.exceptions import Warning, ValidationError, UserError
from odoo.tools import float_compare, float_is_zero, date_utils, email_split, email_re, html_escape, is_html_empty
from odoo.tools import safe_eval
from odoo.tools.misc import formatLang
from . import utils


class AccountMove(models.Model):
    _inherit = "account.move"
    _order = "id desc"

    def _default_fiscal_year(self):
        company_id = self.env.user.company_id
        return company_id.accounting_year.id

    def _default_fiscal_period(self):
        company_id = self.env.user.company_id
        for period in company_id.accounting_year.periods:
            if period.period == '12':
                return period.id
        return False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        if res.get('move_type') in ['out_invoice', 'in_invoice']:
            journal = res.get('journal_id')
            if res.get('receipt_type') == "sale":
                journal_sale = self.env['account.journal'].search(
                    [('type', '=', 'sale'), ('code', 'in', ['FR', 'FR C'])])
                journal = journal_sale.id if journal_sale else journal
            elif res.get('receipt_type') == "purchase":
                journal_purchase = self.env['account.journal'].search(
                    [('type', '=', 'purchase'), ('code', 'in', ['FR', 'FR F'])])
                journal = journal_purchase.id if journal_purchase else journal

            res['journal_id'] = journal
        return res

    year = fields.Many2one(comodel_name='account.fiscal.year', default=lambda l: l._default_fiscal_year())
    period = fields.Many2one(comodel_name="account.fiscal.period", default=lambda l: l._default_fiscal_period())
    payment_difference = fields.Float("Payment Difference")
    # cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")
    # has_cost_center = fields.Boolean(related='company_id.invoice_cost_center')
    facade_period_name = fields.Char(compute='_compute_period')
    period_name = fields.Char(string="Period Name")
    amount_total_wth = fields.Monetary(string='Total Retido', readonly=True, store=True,
                                       compute='_compute_amount_total_wth')
    amount_wth_apply = fields.Monetary(string='Montante Descontado', readonly=True, store=True,
                                       compute='_compute_amount_total_wth')
    partner_deductible_vat = fields.Selection([
        ('none', 'Não deduz'),
        ('100', '100%'),
        ('50', '50%'),
    ], string="Partner Deductible Vat", default='none')
    hash = fields.Char(string="Hash")
    system_entry_date = fields.Datetime(string="System Entry Date")
    hash_control = fields.Char(string="Hash Control", default='1')
    receipt_type = fields.Selection([
        ('sale', 'Venda'), ('purchase', 'Compra')
    ], string="Tipo de Recibo")

    @api.depends('amount_total')
    def _compute_amount_total_wth(self):
        """calcul withholding amount - @author: Hermenegildo Mulonga """
        _withholding = self.get_withholding_tax()
        _amount_wht = 0.0
        if _withholding > 0.0:
            for res in self:
                if res.journal_id.type in ['sale', 'purchase']:
                    _amount_wht = res.amount_total - _withholding
                    res.amount_total_wth = _amount_wht
                    res.amount_wth_apply = _withholding
        return _withholding

    @api.constrains('date', 'invoice_date', 'year')
    def validate_date(self):
        for res in self:
            if res.company_id.accounting_year and res.year:
                if res.company_id.accounting_year == res.year:

                    if not (res.period.start_date <= res.date <= res.period.end_date):
                        raise ValidationError(_("A data %s esta fora do periodo %s \n "
                                                "Inicio: %s - Fim: %s\n Verificar por favor")
                                              % (res.date, res.period.name, res.period.start_date,
                                                 res.period.end_date))
                else:
                    raise ValidationError(_("Ano do registo corrente diferente do Ano fiscal da empresa"))

    # @api.constrains('cost_center')
    # def _check_cost_center(self):
    #     self._prepare_cost_center()

    @api.onchange('year')
    def onchange_year(self):
        for period in self.year.periods:
            if not self.period and period.period == 12:
                self.period = period

    def action_post(self):
        result = super(AccountMove, self).action_post()
        self.hash = utils.generate_hash(4) # Temp
        return result

    @api.constrains('invoice_line_ids')
    def check_field_lines(self):
        for res in self:
            if res.move_type and res.move_type != 'entry':
                if not res.invoice_line_ids or len(res.invoice_line_ids) == 0:
                    raise UserError("Não exite nenhuma linha de factura.\n"
                                    "Adicionar Productos / Serviços nas linhas de factura.")
                for line in res.invoice_line_ids:
                    if line.price_unit < 0:
                        raise UserError("O preço unitário não pode ser negativo.")
                    if line.discount < 0 or line.discount > 100:
                        raise UserError("O desconto deve estar entre 0% - 100%.")
                    if line.quantity < 0:
                        raise UserError("O valor da quantidade deve ser positivo.")

    def _get_starting_sequence(self):
        self.ensure_one()
        if self.journal_id.type in ['sale', 'purchase']:

            if self.journal_id.type == 'sale':
                if utils.check_agt_document_type(self.journal_id.code):
                    starting_sequence = "%s %04d/0" % (self.journal_id.code, self.date.year)
                else:
                    raise UserError("CÓDIGO DO DIÁRIO INVÁLIDO")

                if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
                    if self.move_type == 'out_refund':
                        starting_sequence = starting_sequence.replace(self.journal_id.code, "NC")
                    if self.move_type == 'in_refund':
                        starting_sequence = starting_sequence.replace(self.journal_id.code, "ND")

            elif self.journal_id.type == 'purchase':
                if utils.check_agt_document_type(self.journal_id.code):
                    if self.journal_id.code in ['FT F', 'FR F','FT BI']:
                        starting_sequence = "%s%04d/0" % (self.journal_id.code, self.date.year)
                    else:
                        starting_sequence = "%s %04d/0" % (self.journal_id.code, self.date.year)
                else:
                    raise UserError("CÓDIGO DO DIÁRIO INVÁLIDO")

                if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
                    if self.move_type == 'in_refund':
                        starting_sequence = starting_sequence.replace(self.journal_id.code, "NC")
                    if self.move_type == 'out_refund':
                        starting_sequence = starting_sequence.replace(self.journal_id.code, "ND")
        else:
            starting_sequence = "%s/%04d/%02d/0000" % (self.journal_id.code, self.date.year, self.date.month)
            if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
                starting_sequence = "R" + starting_sequence
        return starting_sequence

    def get_tax_line_details(self):
        """return: data for all taxes - @author: Hermenegildo Mulonga """
        tax_lines_data = []
        for line in self.invoice_line_ids:
            for tax_line in line.tax_ids:
                tax_lines_data.append({
                    'tax_exigibility': tax_line.tax_exigibility,
                    'tax_amount': line.price_subtotal * (tax_line.amount / 100),
                    'base_amount': line.price_subtotal,
                    'tax': tax_line,
                })
        return tax_lines_data

    def get_withholding_tax(self):
        withholding_tax_amount = 0
        for line in self.get_tax_line_details():
            if line['tax_exigibility'] == 'withholding':
                withholding_tax_amount += line['tax_amount']
        return withholding_tax_amount

    def tax_of_invoice(self):
        taxes = []
        for line in self.invoice_line_ids:
            for tax in line.tax_ids:
                taxes.append(tax)
        return list(set(taxes))

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    @api.depends('period')
    def _compute_period(self):
        for res in self:
            res.facade_period_name = res.period.period
            res.period_name = res.period.period

    def get_exchange_rate(self, currency_name):
        currency_id = self.env['res.currency'].sudo().search([('name', '=', currency_name)])
        res = 100.00
        if currency_id:
            for rate in currency_id.rate_ids[-1]:
                if rate.company_rate:
                    res = rate.company_rate
            return res
        return res

    def _prepare_tax_lines_data_for_totals_from_invoice(self, tax_line_id_filter=None, tax_ids_filter=None):
        """ Prepares data to be passed as tax_lines_data parameter of _get_tax_totals() from an invoice.

            NOTE: tax_line_id_filter and tax_ids_filter are used in l10n_latam to restrict the taxes with consider
                  in the totals.

            :param tax_line_id_filter: a function(aml, tax) returning true if tax should be considered on tax move line aml.
            :param tax_ids_filter: a function(aml, taxes) returning true if taxes should be considered on base move line aml.

            :return: A list of dict in the format described in _get_tax_totals's tax_lines_data's docstring.
        """
        self.ensure_one()

        tax_line_id_filter = tax_line_id_filter or (lambda aml, tax: True)
        tax_ids_filter = tax_ids_filter or (lambda aml, tax: True)

        balance_multiplicator = -1 if self.is_inbound() else 1
        tax_lines_data = []

        for line in self.line_ids:
            if line.tax_line_id.tax_exigibility in ['on_invoice']:
                if line.tax_line_id and tax_line_id_filter(line, line.tax_line_id):
                    tax_lines_data.append({
                        'line_key': 'tax_line_%s' % line.id,
                        'tax_amount': line.amount_currency * balance_multiplicator,
                        'tax': line.tax_line_id,
                    })

            if line.tax_ids:
                for base_tax in line.tax_ids.flatten_taxes_hierarchy():
                    if base_tax.tax_exigibility in ['on_invoice']:
                        if tax_ids_filter(line, base_tax):
                            tax_lines_data.append({
                                'line_key': 'base_line_%s' % line.id,
                                'base_amount': line.amount_currency * balance_multiplicator,
                                'tax': base_tax,
                                'tax_affecting_base': line.tax_line_id,
                            })

        return tax_lines_data

    @api.model
    def _prepare_tax_lines_data_for_totals_from_object(self, object_lines, tax_results_function):
        """ Prepares data to be passed as tax_lines_data parameter of _get_tax_totals() from any
            object using taxes. This helper is intended for purchase.order and sale.order, as a common
            function centralizing their behavior.

            :param object_lines: A list of records corresponding to the sub-objects generating the tax totals
                                 (sale.order.line or purchase.order.line, for example)

            :param tax_results_function: A function to be called to get the results of the tax computation for a
                                         line in object_lines. It takes the object line as its only parameter
                                         and returns a dict in the same format as account.tax's compute_all
                                         (most probably after calling it with the right parameters).

            :return: A list of dict in the format described in _get_tax_totals's tax_lines_data's docstring.
        """
        tax_lines_data = []

        for line in object_lines:
            tax_results = tax_results_function(line)

            for tax_result in tax_results['taxes']:
                current_tax = self.env['account.tax'].browse(tax_result['id'])
                """only invoice tax, @author: Hermenegildo Mulonga"""
                if current_tax.tax_exigibility in ['on_invoice']:

                    # Tax line
                    tax_lines_data.append({
                        'line_key': f"tax_line_{line.id}_{tax_result['id']}",
                        'tax_amount': tax_result['amount'],
                        'tax': current_tax,
                    })

                    # Base for this tax line
                    tax_lines_data.append({
                        'line_key': 'base_line_%s' % line.id,
                        'base_amount': tax_results['total_excluded'],
                        'tax': current_tax,
                    })

                    # Base for the taxes whose base is affected by this tax line
                    if tax_result['tax_ids']:
                        affected_taxes = self.env['account.tax'].browse(tax_result['tax_ids'])
                        for affected_tax in affected_taxes:
                            tax_lines_data.append({
                                'line_key': 'affecting_base_line_%s_%s' % (line.id, tax_result['id']),
                                'base_amount': tax_result['amount'],
                                'tax': affected_tax,
                                'tax_affecting_base': current_tax,
                            })
        return tax_lines_data

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        ''' Recompute all lines that depend on others.

        For example, tax lines depends on base lines (lines having tax_ids set). This is also the case of cash rounding
        lines that depend on base lines or tax lines depending on the cash rounding strategy. When a payment term is set,
        this method will auto-balance the move with payment term lines.

        :param recompute_all_taxes: Force the computation of taxes. If set to False, the computation will be done
                                    or not depending on the field 'recompute_tax_line' in lines.
        '''
        for invoice in self:
            # Dispatch lines and pre-compute some aggregated values like taxes.
            expected_tax_rep_lines = set()
            current_tax_rep_lines = set()
            inv_recompute_all_taxes = recompute_all_taxes
            to_remove = self.env['account.move.line']
            for line in invoice.line_ids:
                """only invoice tax, Angola"""
                if line.tax_repartition_line_id.tax_id.tax_exigibility in ['on_payment', 'withholding']:
                    to_remove += line
                if line.recompute_tax_line:
                    inv_recompute_all_taxes = True
                    line.recompute_tax_line = False
                if line.tax_repartition_line_id:
                    current_tax_rep_lines.add(line.tax_repartition_line_id._origin)
                elif line.tax_ids:
                    if invoice.is_invoice(include_receipts=True):
                        is_refund = invoice.move_type in ('out_refund', 'in_refund')
                    else:
                        tax_type = line.tax_ids[0].type_tax_use
                        is_refund = (tax_type == 'sale' and line.debit) or (tax_type == 'purchase' and line.credit)
                    taxes = line.tax_ids._origin.flatten_taxes_hierarchy().filtered(
                        lambda tax: (
                                tax.amount_type == 'fixed' and not invoice.company_id.currency_id.is_zero(tax.amount)
                                or not float_is_zero(tax.amount, precision_digits=4)
                        )
                    )
                    if is_refund:
                        tax_rep_lines = taxes.refund_repartition_line_ids._origin.filtered(
                            lambda x: x.repartition_type == "tax")
                    else:
                        tax_rep_lines = taxes.invoice_repartition_line_ids._origin.filtered(
                            lambda x: x.repartition_type == "tax")
                    for tax_rep_line in tax_rep_lines:
                        expected_tax_rep_lines.add(tax_rep_line)
            delta_tax_rep_lines = expected_tax_rep_lines - current_tax_rep_lines
            invoice.line_ids -= to_remove

            # Compute taxes.
            if inv_recompute_all_taxes:
                invoice._recompute_tax_lines()
            elif recompute_tax_base_amount:
                invoice._recompute_tax_lines(recompute_tax_base_amount=True)
            # elif delta_tax_rep_lines and not self._context.get('move_reverse_cancel'):
            #     invoice._recompute_tax_lines(tax_rep_lines_to_recompute=delta_tax_rep_lines)

            if invoice.is_invoice(include_receipts=True):

                # Compute cash rounding.
                invoice._recompute_cash_rounding_lines()

                # Compute payment terms.
                invoice._recompute_payment_terms_lines()

                # Only synchronize one2many in onchange.
                if invoice != invoice._origin:
                    invoice.invoice_line_ids = invoice.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)

    class AccountMoveLine(models.Model):
        _inherit = 'account.move.line'
        _order = "id asc"

        # cash_flow = fields.Many2one(string="Cash Flow", related='account_id.cash_flow', store=True)
        # iva_plan = fields.Many2one(string="Plan IVA", related='account_id.iva_plan', store=True)
        # fiscal_plan = fields.Many2one(string="Plan Fiscal", related='account_id.fiscal_plan', store=True)
        # has_cost_center = fields.Boolean(related='account_id.has_cost_center')
        # has_cash_flow = fields.Boolean(related='account_id.has_cash_flow')
        # has_iva = fields.Boolean(related='account_id.has_iva')
        # has_fiscal_plan = fields.Boolean(related='account_id.has_fiscal_plan')
        move_id_state = fields.Selection(related='move_id.state', string="state")
        period = fields.Many2one(comodel_name="account.fiscal.period", compute='_store_period', store=True)
        # cost_center = fields.Many2one(comodel_name="account.cost.center", related='move_id.cost_center',
        #                               string="Cost Center", store=True)

        @api.depends('move_id')
        def _store_period(self):
            for res in self:
                if res.move_id.period:
                    res.period = res.move_id.period
