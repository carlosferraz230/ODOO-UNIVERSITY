from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ss = fields.Char('Nº SS')
    hr_mobile = fields.Char(string="Mobile")
    hr_phone = fields.Char(string="Phone")
    hr_manager = fields.Char(string="RH Responsible")
    hr_general_manager = fields.Char(string="General Manager")
