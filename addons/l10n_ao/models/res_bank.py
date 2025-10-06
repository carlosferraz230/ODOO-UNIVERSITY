from odoo import models, fields


class ResBank(models.Model):
    _inherit = "res.bank"

    code = fields.Char("Code", size=6)
    bic = fields.Char("BIC", size=25)
    of_company = fields.Boolean('Of Company')
    company_bank_account = fields.Char('Company Bank Account')

    _sql_constraints = [
        ('name_code_uniq', 'unique(code)', 'The code of the bank must be unique!')
    ]


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    show_doc = fields.Boolean("Show on documents")
    iban_number = fields.Char(string="IBAN", default="AO06")
