from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_note = fields.Many2one(comodel_name='account.note', string='Account Note')

    def write(self, vals):
        if vals.get('code'):
            vals['code'] = vals['code'].replace(" ", "")
        return super(AccountAccount, self).write(vals)

    @api.model
    def create(self, vals):
        if vals.get('code'):
            vals['code'] = vals['code'].replace(" ", "")
        return super(AccountAccount, self).create(vals)