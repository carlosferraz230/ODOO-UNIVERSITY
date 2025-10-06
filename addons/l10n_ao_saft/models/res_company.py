from odoo import api, models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    tax_entity = fields.Char("Entity")
    agt_cert_number = fields.Char("Software Validation Number", default="00/AGT/2024")
    agt_product_name = fields.Char("Product ID", default="TIBLAC ODOO ANGOLA/TICBLAC SOLUTION")
    agt_product_version = fields.Char("Product Version", default="15.0")
    audit_file_version = fields.Char("Audit File Version", readonly=True, default="1.01_01")
    product_company_name = fields.Char("Product Company Name",
                                       default="TICBLAC SOLUTION - SERVIÇOS, LD")
    product_company_website = fields.Char("Website", default="www.ticblac.com")
    product_company_tax_id = fields.Char("Product Company Tax ID", default="5001243772")
    agt_regime = fields.Selection([
        ('EI', 'Exclusão de IVA'),
        ('RC', 'Regime de caixa'),
        ('S', 'Simplificado'),
        ('G', 'Geral')
    ], 'Regime')
    company_registry = fields.Char(string="company registry")
