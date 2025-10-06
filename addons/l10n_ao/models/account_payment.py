from odoo import models, api, fields, _
from . import amount_to_text_pt
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"
    _description = "Payment in Angola"

    amount_text = fields.Char(string="Amount in Words", compute="_get_amount_in_words", store=True)
    number = fields.Char(string="Número")
    is_advanced = fields.Boolean(string="Is Advanced ?")
    deductible_wth = fields.Monetary(string="Withhold Apply", currency_field='currency_id')
    deductible_vat = fields.Monetary(string="Deductible VAT", currency_field='currency_id')
    partner_deductible_vat = fields.Selection([
        ('none', 'Não deduz'),
        ('100', '100%'),
        ('50', '50%'),
    ], string="Partner Deductible Vat", default='none')

    @api.model_create_multi
    def create(self, vals_list):
        result = super(AccountPayment, self).create(vals_list)
        sequence = self.env['ir.sequence'].next_by_code('account.payment.customer') or _('RG')
        result.number = sequence
        return result

    @api.depends('amount', 'journal_id')
    def _get_amount_in_words(self):
        for payment in self:
            currency_name = "AOA"
            if payment.amount > 0 and payment.currency_id:
                if payment.currency_id.name == "AOA":
                    currency_name = "Kwanzas"
                if payment.currency_id.name == "EUR":
                    currency_name = "Euros"
                if payment.currency_id.name == "USD":
                    currency_name = "Dolares Americanos"
                payment.amount_text = amount_to_text_pt.amount_to_text(payment.amount, currency_name)

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    def get_exchange_rate(self, currency_name):
        currency_id = self.env['res.currency'].sudo().search([('name', '=', currency_name)])
        res = 100.00
        for rate in currency_id.rate_ids[-1]:
            if rate.company_rate:
                res = rate.company_rate
        return res

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one outstanding payments/receipts account.",
                        move.display_name,
                    ))

                if len(counterpart_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one receivable/payable account (with an exception of "
                        "internal transfers).",
                        move.display_name,
                    ))

                if writeoff_lines and len(writeoff_lines.account_id) != 1:
                    """ Check if there are more than 2 accounts , 
                        this is for the cases where the customer withheld VAT and industrial tax
                        @autor: Hermenegildo Mulonga
                    """
                    if len(writeoff_lines.account_id) > 2:
                        raise UserError(_(
                            "Journal Entry %s is not valid. In order to proceed, "
                            "all optional journal items must share the same account.",
                            move.display_name,
                        ))

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same currency.",
                        move.display_name,
                    ))

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same partner.",
                        move.display_name,
                    ))

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

