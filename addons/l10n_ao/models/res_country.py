
from odoo import models, fields, api, _


class ResStateCounty(models.Model):
    _name = "res.country.state.county"
    _description = "Country State County"

    state_id = fields.Many2one(comodel_name='res.country.state', string='Province', required=True)
    name = fields.Char(string='County Name', required=True)
    code = fields.Char(string='County Code', help='The County code.', required=True)


class ResCountryStateCounty(models.Model):
    _name = "res.country.state.county.district"
    _description = "Country State County District"

    county_id = fields.Many2one(comodel_name='res.country.state.county', string='Province', required=True)
    name = fields.Char(string='County Name', required=True)
    code = fields.Char(string='District Code', help='The District code.', required=True)

    _sql_constraints = [
        ('name_code_uniq', 'unique(county_id, code)', 'The code of the state must be unique by country !')
    ]


class ResState(models.Model):
    _inherit = "res.country.state"

    county_ids = fields.One2many("res.country.state.county", "state_id")
