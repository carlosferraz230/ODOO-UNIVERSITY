from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SAFTAccountTax(models.Model):
    _inherit = "account.tax"

    country_region = fields.Char(string="Região Fiscal", default="AO", )
    tax_type = fields.Selection(string="TAX Type", selection=[
        ('IVA', 'IVA'), ('IS', 'Imp do Selo'),
        ('NS', 'Não sujeição a IVA ou IS')
    ], required=True, default="NS", )
    tax_code = fields.Selection(string="Tax Code", selection=[
        ('RED', 'Reduzida'),
        ('NOR', 'Normal'),
        ('INT', 'Intermédia'),
        ('ISE', 'Isenta'),
        ('OUT', 'Outra')
    ], required=True, default="NOR")
    tax_type_with = fields.Selection(string="Withholding Type",
                                     selection=[
                                         ('IRT', 'Imposto sobre o rendimento de trabalho'),
                                         ('II', 'Imposto Industrial'),
                                         ("IS", "Imposto do Selo")
                                     ], required=False, default="II")
    expiration_date = fields.Date(string="Data Expiração", )
    exemption_reason = fields.Char(string="Motivo da isenção", size=60,
                                   help="No caso de IVA isento, indique qual a norma do codigo do IVA que autribui a isenção")

    def get_saft_data(self):
        """
        Generate SAFT- AO compliant tax table data.
        """

        def format_tax_entry(tax):
            """
            Format a single tax entry.
            """
            tax_entry = {
                'TaxType': tax.tax_type,
                'TaxCountryRegion': 'AO',
                'TaxCode': tax.tax_code,
                'Description': tax.name,
            }

            if tax.amount_type in ["percent", "division"]:
                tax_entry['TaxPercentage'] = f"{tax.amount:.2f}"
            elif tax.amount_type == "fixed":
                tax_entry['TaxAmount'] = f"{tax.amount:.2f}"

            if tax.expiration_date:
                tax_entry['TaxExpirationDate'] = fields.Date.to_string(tax.expiration_date)

            return tax_entry

        # Base result structure
        result = {
            'TaxTable': {
                'TaxTableEntry': [format_tax_entry(tax) for tax in self],
            }
        }

        return result
