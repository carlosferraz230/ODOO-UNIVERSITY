# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError


class PosSession(models.Model):
    _inherit = ['pos.session']

    def print_session_close_report(self):
        return self.env.ref('l10n_ao_pos.report_pos_session_close').report_action(self)

    def get_total_per_payments(self):
        totals_per_payments = []
        journals = self.env['account.journal'].search([("type", 'in', ['cash', 'bank'])]).pos_payment_method_ids
        for journal in journals:
            payment = {
                'type': journal.id,
                'name': journal.name,
                'amount': 0.00,
                'currency': ''
            }
            for line in self.order_ids:
                for payment_type in line.payment_ids:
                    if payment_type.payment_method_id.id == payment['type']:
                        payment['amount'] += payment_type.amount
                        payment['currency'] = line.currency_id.symbol
            totals_per_payments.append(payment)
        return totals_per_payments
