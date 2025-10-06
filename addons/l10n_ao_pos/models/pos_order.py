from odoo import models, api, _, tools, fields
from odoo.exceptions import ValidationError
from . import utils
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def create(self, values):
        result = super(PosOrder, self).create(values)
        if not result.partner_id:
            partner = self.env['res.partner'].search([('ref', '=', 'CF')])
            result.partner_id = partner
        return result

    @api.model
    def _order_fields(self, ui_order):
        ui_order['to_invoice'] = True
        return super()._order_fields(ui_order)

    @api.model
    def get_hash(self):
        invoice_id = self.env.context.get('invoice_id')
        res = self.env['account.move'].search([('id', '=', invoice_id)])
        hash_number = res.hash or 'asdfghjklpoiuytrewqzxcvbnmlkjhgfdsartyuioplkjhgfdsazxcvb'
        return hash_number[1] + hash_number[11] + hash_number[21] + hash_number[31]

    def _prepare_invoice_vals(self):
        result = super(PosOrder, self)._prepare_invoice_vals()

        result["system_entry_date"] = fields.Datetime.now()
        # result["hash_control"] = self.company_id.key_version or '1'
        content_hash = self.get_content_to_sign(result)
        sequence_number = self.name.replace('FT', '').split('/')
        result["sequence_number"] = sequence_number[-1]
        content_signed = utils.signer(content_hash)
        if not content_signed:
            raise ValidationError(_("Problem Signing Invoice"))
        result["hash"] = content_signed

        return result

    def get_content_to_sign(self, result):
        domain = [
            ('state', 'in', ['posted', ]),
            ('move_type', 'in', ['in_invoice', 'in_refund', 'out_invoice', 'out_refund']),
        ]

        if self.env.user.has_group('base.group_multi_company'):
            domain.append(('company_id', '=', self.company_id.id))

        system_entry_date = fields.Datetime.now().isoformat(sep='T', timespec='auto')
        _last_invoices = self.env['account.move'].search(domain, order='sequence_number asc')

        total = utils.gross_total(self.amount_total)
        last_invoice_hash = ""

        if _last_invoices:
            last_invoice_hash = _last_invoices[-1].hash or 'asdfghjklpoiuytrewqzxcvbnmlkjhgfdsartyuioplkjhgfdsazxcvb'
            content = (str(result["invoice_date"]), system_entry_date, self.name, str(total), last_invoice_hash)
            return ";".join(content)
        else:
            content = (
                str(result["invoice_date"]), system_entry_date, self.name, str(total))
            return ";".join(content) + ';'
