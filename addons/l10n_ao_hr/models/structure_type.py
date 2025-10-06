from odoo import fields, models, api


class StructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    effetive_contract = fields.Boolean(
        string='Efetive contract',
        required=False)
    provider_contract = fields.Boolean(
        string='Provider contract',
        required=False)



