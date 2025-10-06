from odoo import fields, models, api, _
from odoo.exceptions import UserError, AccessError


class AOAccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'
    _description = 'Add default prefix to company'

    partner_receivable_code_prefix = fields.Char('Partner receivable Account Code Prefix', size=64,
                                                 help=_("""This prefix will allow to automatically 
                                                     create the client chart account"""))
    partner_payable_code_prefix = fields.Char('Partner payable Account Code Prefix', size=64,
                                              help=_("""This prefix will allow to automatically
                                               create the supplier chart account"""))
    fpartner_receivable_code_prefix = fields.Char('Foreign Partner receivable Account Code Prefix', size=64,
                                                  help=_("""This prefix will allow to automatically
                                                   create the client chart account"""))
    fpartner_payable_code_prefix = fields.Char('Foreign Partner payable Account Code Prefix', size=64,
                                               help=_("""This prefix will allow to automatically 
                                               create the supplier chart account"""))

    tax_withhold_journal_id = fields.Many2one('account.journal', _("Tax Withhold Journal"), required=False)
    tax_withhold_received_account_id = fields.Many2one('account.account.template', "Withhold DAR Received Account")
    tax_withhold_sent_account_id = fields.Many2one('account.account.template', "Withhold DAR Sent Account")
    property_account_income_credit_id = fields.Many2one('account.account.template', 'Category of Income Credit Account')
    property_account_expense_credit_id = fields.Many2one('account.account.template',
                                                         'Category of Expense Credit Account')

    tax_cash_basis_account_id = fields.Many2one('account.account.template', 'Account Id for Tax Cash Basis')

    # Override the journal creation codes for default
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        def _get_default_account(journal_vals, type='debit'):
            # Get the default accounts
            default_account = False
            if journal['type'] == 'sale':
                default_account = acc_template_ref.get(self.property_account_income_categ_id.id)
            elif journal['type'] == 'purchase':
                default_account = acc_template_ref.get(self.property_account_expense_categ_id.id)
            elif journal['type'] == 'general' and journal['code'] == _('CAMB'):
                if type == 'credit':
                    default_account = acc_template_ref.get(self.income_currency_exchange_account_id.id)
                else:
                    default_account = acc_template_ref.get(self.expense_currency_exchange_account_id.id)
            elif journal['type'] == 'general' and journal['code'] == _('TAX'):
                default_account = acc_template_ref.get(self.tax_cash_basis_account_id.id)

            return default_account

        journals = [
            {'name': _('Facturas de Clientes'), 'type': 'sale', 'code': _('FT'), 'favorite': True, 'color': 11,
             'sequence': 5},
            {'name': _('Facturas de Fornecedor'), 'type': 'purchase', 'code': _('FT BIL'), 'favorite': True, 'color': 11,
             'sequence': 6},
            {'name': _('Operações Diversas'), 'type': 'general', 'code': _('DIV'), 'favorite': True,
             'sequence': 7},
            {'name': _('Diferença cambial'), 'type': 'general', 'code': _('CAMB'), 'favorite': False,
             'sequence': 9},
            {'name': _('Cash Basis Taxes'), 'type': 'general', 'code': _('TAX'), 'favorite': False,
             'sequence': 10}
        ]
        if journals_dict != None:
            journals.extend(journals_dict)

        self.ensure_one()
        journal_data = []
        for journal in journals:
            vals = {
                'type': journal['type'],
                'name': journal['name'],
                'code': journal['code'],
                'company_id': company.id,
                'default_account_id': _get_default_account(journal),
                'show_on_dashboard': journal['favorite'],
                'color': journal.get('color', False),
                'sequence': journal['sequence']
            }
            journal_data.append(vals)
        return journal_data

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        # Set by default 4821 account
        # @utor: Hermenegildo Mulonga, Angola Luanda 18/03/22
        res = super(AOAccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
        if company.account_fiscal_country_id.code == 'AO':
            company.automatic_partner_account = True
            account = self.env['account.account'].search([
                ('code', '=', '4821'),
                ('company_id', '=', self.env.company.id)
            ])
            if account:
                company.account_journal_suspense_account_id = account
        return res
