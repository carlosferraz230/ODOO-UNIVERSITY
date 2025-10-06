from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    inv_signed = fields.Boolean('Sign Invoice')
    partner_receivable_code_prefix = fields.Char('Partner receivable Account Code Prefix', size=64, default='311211')
    partner_payable_code_prefix = fields.Char('Partner payable Account Code Prefix', size=64, default='32121')
    fpartner_receivable_code_prefix = fields.Char('F. Partner receivable Account Code Prefix', size=64, default='31122')
    fpartner_payable_code_prefix = fields.Char('F. Partner payable Account Code Prefix', size=64, default='32122')
    automatic_partner_account = fields.Boolean(string="Create Automatic Account Partners?", default=True)
    accounting_year = fields.Many2one(comodel_name='account.fiscal.year', string="Accounting Year", required=False)
    account_opening_date = fields.Date(string='Opening Date', related='accounting_year.date_from', required=True,
                                       help="That is the date of the opening entry.")
    key_version = fields.Char(string='Key Version', default='1')

    @api.model
    def create_op_move_if_non_existant(self):
        """ Creates an empty opening move in 'draft' state for the current company
        if there wasn't already one defined. For this, the function needs at least
        one journal of type 'general' to exist (required by account.move).
        """
        self.ensure_one()
        if not self.account_opening_move_id:
            default_journal = self.env['account.journal'].search(
                [('type', '=', 'general'), ('company_id', '=', self.id)], limit=1)

            if not default_journal:
                raise UserError(
                    _("Please install a chart of accounts or create a miscellaneous journal before proceeding."))

            if not self.account_opening_date: self.account_opening_date = fields.Date.context_today(self).replace(
                month=1, day=1)
            opening_date = self.account_opening_date - timedelta(days=1)

            self.account_opening_move_id = self.env['account.move'].create({
                'ref': _('Opening Journal Entry'),
                'company_id': self.id,
                'journal_id': default_journal.id,
                'date': opening_date,
            })